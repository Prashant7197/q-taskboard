import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from users.models import User
from projects.models import Comment, Project, Membership, Task


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='meera@taskboard.dev', name='Meera Iyer', password='password123')


@pytest.fixture
def auth_client(client, user):
    response = client.post('/api/auth/login', {
        'email': 'meera@taskboard.dev',
        'password': 'password123',
    }, format='json')
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']}")
    return client


@pytest.mark.django_db
class TestProjects:
    def test_create_project(self, auth_client, user):
        response = auth_client.post('/api/projects', {'name': 'My Project'}, format='json')
        assert response.status_code == 201
        assert response.data['project']['name'] == 'My Project'

    def test_list_only_returns_member_projects(self, auth_client, user):
        p1 = Project.objects.create(name='Mine', owner=user)
        Membership.objects.create(user=user, project=p1, role='admin')
        other = User.objects.create_user(email='other@example.com', name='Other', password='password123')
        p2 = Project.objects.create(name='Not Mine', owner=other)
        Membership.objects.create(user=other, project=p2, role='admin')

        response = auth_client.get('/api/projects')
        assert response.status_code == 200
        names = [p['name'] for p in response.data['projects']]
        assert 'Mine' in names
        assert 'Not Mine' not in names

    def test_get_project_detail(self, auth_client, user):
        project = Project.objects.create(name='My Project', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')

        response = auth_client.get(f'/api/projects/{project.id}')
        assert response.status_code == 200
        assert response.data['project']['name'] == 'My Project'

    def test_non_member_cannot_view_project(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='Private', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.get(f'/api/projects/{project.id}')
        assert response.status_code == 403


@pytest.mark.django_db
class TestTasks:
    @pytest.mark.parametrize('role', ['admin', 'member', 'viewer'])
    def test_project_roles_can_search_only_their_project_tasks(self, client, user, role):
        project = Project.objects.create(name='Accessible', owner=user)
        Membership.objects.create(user=user, project=project, role=role)
        matching_task = Task.objects.create(
            project=project, title='Release checklist', created_by=user
        )
        other_owner = User.objects.create_user(
            email='other@example.com', name='Other', password='password123'
        )
        other_project = Project.objects.create(name='Private', owner=other_owner)
        Membership.objects.create(user=other_owner, project=other_project, role='admin')
        Task.objects.create(
            project=other_project, title='Release secret', created_by=other_owner
        )
        client.force_authenticate(user=user)

        response = client.get(f'/api/projects/{project.id}/tasks', {'q': 'Release'})

        assert response.status_code == 200
        assert [str(task['id']) for task in response.data['tasks']] == [str(matching_task.id)]

    def test_non_member_cannot_search_project_tasks(self, client, user):
        owner = User.objects.create_user(
            email='owner@example.com', name='Owner', password='password123'
        )
        project = Project.objects.create(name='Private', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        Task.objects.create(project=project, title='Private task', created_by=owner)
        client.force_authenticate(user=user)

        response = client.get(f'/api/projects/{project.id}/tasks', {'q': 'Private'})

        assert response.status_code == 403

    def test_search_input_cannot_escape_project_scope(self, client, user):
        project = Project.objects.create(name='Accessible', owner=user)
        Membership.objects.create(user=user, project=project, role='viewer')
        Task.objects.create(project=project, title='Visible task', created_by=user)
        other_owner = User.objects.create_user(
            email='other@example.com', name='Other', password='password123'
        )
        other_project = Project.objects.create(name='Private', owner=other_owner)
        Membership.objects.create(user=other_owner, project=other_project, role='admin')
        Task.objects.create(
            project=other_project, title='Cross-project secret', created_by=other_owner
        )
        client.force_authenticate(user=user)

        response = client.get(
            f'/api/projects/{project.id}/tasks', {'q': "' OR 1=1) -- "}
        )

        assert response.status_code == 200
        assert response.data['tasks'] == []

    def test_create_task(self, auth_client, user):
        project = Project.objects.create(name='P', owner=user)
        Membership.objects.create(user=user, project=project, role='admin')

        response = auth_client.post(f'/api/projects/{project.id}/tasks', {'title': 'Do a thing'}, format='json')
        assert response.status_code == 201
        assert response.data['task']['title'] == 'Do a thing'

    def test_viewers_cannot_create_tasks(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        Membership.objects.create(user=user, project=project, role='viewer')

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.post(f'/api/projects/{project.id}/tasks', {'title': 'A task'}, format='json')
        assert response.status_code == 403

    def test_delete_task_requires_membership(self, client, user):
        owner = User.objects.create_user(email='owner@example.com', name='Owner', password='password123')
        project = Project.objects.create(name='P', owner=owner)
        Membership.objects.create(user=owner, project=project, role='admin')
        task = Task.objects.create(project=project, title='A task', created_by=owner)

        resp = client.post('/api/auth/login', {'email': 'meera@taskboard.dev', 'password': 'password123'}, format='json')
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['token']}")

        response = client.delete(f'/api/tasks/{task.id}')
        assert response.status_code == 403


@pytest.mark.django_db
class TestTaskComments:
    def make_task(self, user, role='admin'):
        project = Project.objects.create(name='Project', owner=user)
        Membership.objects.create(user=user, project=project, role=role)
        task = Task.objects.create(project=project, title='Task', created_by=user)
        return project, task

    @pytest.mark.parametrize('role', ['admin', 'member'])
    def test_admin_and_member_can_list_comments(self, client, user, role):
        _, task = self.make_task(user, role)
        comment = Comment.objects.create(task=task, author=user, body='An update')
        client.force_authenticate(user=user)

        response = client.get(f'/api/tasks/{task.id}/comments')

        assert response.status_code == 200
        assert [item['id'] for item in response.data['comments']] == [str(comment.id)]

    @pytest.mark.parametrize('role', ['admin', 'member'])
    def test_admin_and_member_can_create_comments(self, client, user, role):
        _, task = self.make_task(user, role)
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/tasks/{task.id}/comments', {'body': 'New comment'}, format='json'
        )

        assert response.status_code == 201
        assert response.data['comment']['body'] == 'New comment'
        assert response.data['comment']['created_at']

    def test_viewer_can_list_comments(self, client, user):
        _, task = self.make_task(user, 'viewer')
        Comment.objects.create(task=task, author=user, body='Visible comment')
        client.force_authenticate(user=user)

        response = client.get(f'/api/tasks/{task.id}/comments')

        assert response.status_code == 200
        assert response.data['comments'][0]['body'] == 'Visible comment'

    def test_viewer_cannot_create_comments(self, client, user):
        _, task = self.make_task(user, 'viewer')
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/tasks/{task.id}/comments', {'body': 'Not allowed'}, format='json'
        )

        assert response.status_code == 403
        assert not Comment.objects.exists()

    @pytest.mark.parametrize('method', ['get', 'post'])
    def test_outsider_cannot_list_or_create_comments(self, client, user, method):
        owner = User.objects.create_user(
            email='owner@example.com', name='Owner', password='password123'
        )
        _, task = self.make_task(owner)
        client.force_authenticate(user=user)

        response = getattr(client, method)(
            f'/api/tasks/{task.id}/comments', {'body': 'Not allowed'}, format='json'
        )

        assert response.status_code == 403
        assert not Comment.objects.exists()

    def test_comments_are_listed_oldest_first(self, client, user):
        _, task = self.make_task(user)
        newer = Comment.objects.create(task=task, author=user, body='Newer')
        older = Comment.objects.create(task=task, author=user, body='Older')
        now = timezone.now()
        Comment.objects.filter(id=newer.id).update(created_at=now)
        Comment.objects.filter(id=older.id).update(created_at=now - timedelta(minutes=1))
        client.force_authenticate(user=user)

        response = client.get(f'/api/tasks/{task.id}/comments')

        assert response.status_code == 200
        assert [item['body'] for item in response.data['comments']] == ['Older', 'Newer']

    def test_comment_author_is_always_authenticated_user(self, client, user):
        _, task = self.make_task(user)
        other = User.objects.create_user(
            email='other@example.com', name='Other', password='password123'
        )
        client.force_authenticate(user=user)

        response = client.post(
            f'/api/tasks/{task.id}/comments',
            {'body': 'Mine', 'author': {'id': str(other.id)}, 'author_id': str(other.id)},
            format='json',
        )

        assert response.status_code == 201
        comment = Comment.objects.get()
        assert comment.author == user
        assert response.data['comment']['author']['id'] == str(user.id)

    @pytest.mark.parametrize('method', ['patch', 'delete'])
    def test_comment_edit_and_delete_methods_are_unavailable(self, client, user, method):
        _, task = self.make_task(user)
        comment = Comment.objects.create(task=task, author=user, body='Permanent')
        client.force_authenticate(user=user)

        response = getattr(client, method)(
            f'/api/tasks/{task.id}/comments', {'body': 'Changed'}, format='json'
        )

        assert response.status_code == 405
        comment.refresh_from_db()
        assert comment.body == 'Permanent'
