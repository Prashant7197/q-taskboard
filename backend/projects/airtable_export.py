import os
import time

from pyairtable import Api
from requests.exceptions import ConnectionError, RequestException, Timeout


TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
PERMANENT_STATUS_CODES = {400, 401, 403}
BATCH_SIZE = 10
MAX_ATTEMPTS = 3


class AirtableConfigurationError(Exception):
    pass


class AirtableExportError(Exception):
    pass


def get_airtable_table():
    api_key = os.environ.get('AIRTABLE_API_KEY')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    table_name = os.environ.get('AIRTABLE_TABLE_NAME')
    if not api_key or not base_id or not table_name:
        raise AirtableConfigurationError(
            'AIRTABLE_API_KEY, AIRTABLE_BASE_ID, and AIRTABLE_TABLE_NAME are required'
        )
    return Api(api_key, retry_strategy=False).table(base_id, table_name)


def _status_code(error):
    response = getattr(error, 'response', None)
    return getattr(response, 'status_code', None)


def _is_transient(error):
    status_code = _status_code(error)
    if status_code is not None:
        return status_code in TRANSIENT_STATUS_CODES
    return isinstance(error, (ConnectionError, Timeout, RequestException))


def _with_retry(operation, sleep=time.sleep):
    for attempt in range(MAX_ATTEMPTS):
        try:
            return operation()
        except Exception as error:
            if not _is_transient(error) or attempt == MAX_ATTEMPTS - 1:
                raise
            sleep(0.25 * (2 ** attempt))


def _task_fields(task):
    return {
        'Task ID': str(task.id),
        'Project ID': str(task.project_id),
        'Title': task.title,
        'Description': task.description or '',
        'Status': task.status,
        'Assignee': task.assignee.email if task.assignee else '',
        'Created By': task.created_by.email,
        'Position': task.position,
    }


def _chunks(items):
    for start in range(0, len(items), BATCH_SIZE):
        yield items[start:start + BATCH_SIZE]


def _record_error(task, action, error):
    return {
        'taskId': str(task.id),
        'action': action,
        'error': str(error),
    }


def _write_batch(table, entries, action, summary, sleep):
    if action == 'created':
        payload = [fields for _, fields, _ in entries]
        batch_operation = lambda: table.batch_create(payload)
    else:
        payload = [
            {'id': record_id, 'fields': fields}
            for _, fields, record_id in entries
        ]
        batch_operation = lambda: table.batch_update(payload)

    try:
        _with_retry(batch_operation, sleep)
        summary[action] += len(entries)
        return
    except Exception as error:
        if _status_code(error) in PERMANENT_STATUS_CODES:
            summary['failed'] += len(entries)
            summary['errors'].extend(
                _record_error(task, action, error)
                for task, _, _ in entries
            )
            return

    for task, fields, record_id in entries:
        try:
            if action == 'created':
                _with_retry(lambda: table.create(fields), sleep)
            else:
                _with_retry(lambda: table.update(record_id, fields), sleep)
            summary[action] += 1
        except Exception as error:
            summary['failed'] += 1
            summary['errors'].append(_record_error(task, action, error))


def export_project_tasks(tasks, table=None, sleep=time.sleep):
    table = table or get_airtable_table()
    tasks = list(tasks)
    summary = {
        'total': len(tasks),
        'created': 0,
        'updated': 0,
        'failed': 0,
        'errors': [],
    }

    try:
        existing_records = _with_retry(
            lambda: table.all(fields=['Task ID']),
            sleep,
        )
    except Exception as error:
        raise AirtableExportError(f'failed to read existing Airtable records: {error}') from error

    records_by_task_id = {
        str(record.get('fields', {}).get('Task ID')): record['id']
        for record in existing_records
        if record.get('fields', {}).get('Task ID') and record.get('id')
    }

    creates = []
    updates = []
    for task in tasks:
        fields = _task_fields(task)
        record_id = records_by_task_id.get(str(task.id))
        if record_id:
            updates.append((task, fields, record_id))
        else:
            creates.append((task, fields, None))

    for entries in _chunks(creates):
        _write_batch(table, entries, 'created', summary, sleep)
    for entries in _chunks(updates):
        _write_batch(table, entries, 'updated', summary, sleep)

    return summary
