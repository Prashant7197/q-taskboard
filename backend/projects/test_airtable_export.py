import pytest
from rest_framework.test import APIClient

from projects.airtable_export import export_project_tasks
from projects.airtable_mock import MockAirtableError, MockAirtableTable
from projects.models import Membership, Project, Task
from users.models import User


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='exporter@example.com', name='Exporter', password='password123'
    )


@pytest.fixture
def airtable(monkeypatch):
    table = MockAirtableTable()
    monkeypatch.setattr('projects.airtable_export.get_airtable_table', lambda: table)
    return table


def make_project(user, role='admin'):
    project = Project.objects.create(name='Export Project', owner=user)
    Membership.objects.create(user=user, project=project, role=role)
    return project


def make_task(project, user, title='Task'):
    return Task.objects.create(project=project, title=title, created_by=user)


@pytest.mark.django_db
class TestExportEndpoint:
    @pytest.mark.parametrize('role', ['admin', 'member'])
    def test_admin_and_member_can_export(self, client, user, airtable, role):
        project = make_project(user, role)
        make_task(project, user)
        client.force_authenticate(user=user)

        response = client.post(f'/api/projects/{project.id}/export')

        assert response.status_code == 200
        assert response.data == {
            'total': 1, 'created': 1, 'updated': 0, 'failed': 0, 'errors': []
        }

    def test_viewer_cannot_export(self, client, user, airtable):
        project = make_project(user, 'viewer')
        client.force_authenticate(user=user)

        response = client.post(f'/api/projects/{project.id}/export')

        assert response.status_code == 403
        assert airtable.calls['all'] == 0

    def test_outsider_cannot_export(self, client, user, airtable):
        owner = User.objects.create_user(
            email='owner@example.com', name='Owner', password='password123'
        )
        project = make_project(owner)
        client.force_authenticate(user=user)

        response = client.post(f'/api/projects/{project.id}/export')

        assert response.status_code == 403
        assert airtable.calls['all'] == 0

    def test_exports_all_tasks_from_only_the_requested_project(self, client, user, airtable):
        project = make_project(user)
        Task.objects.bulk_create([
            Task(project=project, title=f'Task {index}', created_by=user)
            for index in range(1001)
        ])
        other_project = Project.objects.create(name='Other', owner=user)
        make_task(other_project, user, 'Must not export')
        client.force_authenticate(user=user)

        response = client.post(f'/api/projects/{project.id}/export')

        assert response.status_code == 200
        assert response.data['total'] == 1001
        assert response.data['created'] == 1001
        assert len(airtable.records) == 1001
        assert {fields['Project ID'] for fields in airtable.records.values()} == {str(project.id)}

    def test_second_export_updates_without_duplicates(self, client, user, airtable):
        project = make_project(user)
        task = make_task(project, user, 'First title')
        client.force_authenticate(user=user)

        first = client.post(f'/api/projects/{project.id}/export')
        task.title = 'Updated title'
        task.save(update_fields=['title'])
        second = client.post(f'/api/projects/{project.id}/export')

        assert first.data['created'] == 1
        assert second.data == {
            'total': 1, 'created': 0, 'updated': 1, 'failed': 0, 'errors': []
        }
        assert len(airtable.records) == 1
        assert next(iter(airtable.records.values()))['Title'] == 'Updated title'


@pytest.mark.django_db
class TestAirtableExportService:
    def test_transient_errors_are_retried_with_bounded_backoff(self, user):
        project = make_project(user)
        task = make_task(project, user)
        table = MockAirtableTable()
        table.queue_failure('batch_create', MockAirtableError('rate limited', 429))
        table.queue_failure('batch_create', MockAirtableError('unavailable', 503))
        delays = []

        summary = export_project_tasks([task], table=table, sleep=delays.append)

        assert summary['created'] == 1
        assert table.calls['batch_create'] == 3
        assert delays == [0.25, 0.5]

    def test_permanent_errors_are_not_retried(self, user):
        project = make_project(user)
        task = make_task(project, user)
        table = MockAirtableTable()
        table.queue_failure('batch_create', MockAirtableError('bad request', 400))

        summary = export_project_tasks([task], table=table, sleep=lambda _: None)

        assert summary['failed'] == 1
        assert table.calls['batch_create'] == 1
        assert table.calls['create'] == 0

    def test_one_record_failure_does_not_stop_other_records(self, user):
        project = make_project(user)
        good = make_task(project, user, 'Good')
        bad = make_task(project, user, 'Bad')
        table = MockAirtableTable()
        table.failed_task_ids.add(str(bad.id))

        summary = export_project_tasks([good, bad], table=table, sleep=lambda _: None)

        assert summary['total'] == 2
        assert summary['created'] == 1
        assert summary['failed'] == 1
        assert summary['errors'][0]['taskId'] == str(bad.id)
        assert len(table.records) == 1

    def test_summary_counts_created_updated_and_failed(self, user):
        project = make_project(user)
        existing = make_task(project, user, 'Existing')
        new = make_task(project, user, 'New')
        bad = make_task(project, user, 'Bad')
        table = MockAirtableTable()
        table._store({
            'Task ID': str(existing.id),
            'Project ID': str(project.id),
            'Title': 'Old title',
        })
        table.failed_task_ids.add(str(bad.id))

        summary = export_project_tasks(
            [existing, new, bad], table=table, sleep=lambda _: None
        )

        assert summary == {
            'total': 3,
            'created': 1,
            'updated': 1,
            'failed': 1,
            'errors': [{
                'taskId': str(bad.id),
                'action': 'created',
                'error': 'invalid record',
            }],
        }
