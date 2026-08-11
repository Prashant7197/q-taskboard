class MockAirtableError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.response = None
        if status_code is not None:
            self.response = type('Response', (), {'status_code': status_code})()


class MockAirtableTable:
    def __init__(self):
        self.records = {}
        self.next_id = 1
        self.calls = {'all': 0, 'batch_create': 0, 'batch_update': 0, 'create': 0, 'update': 0}
        self.failures = {name: [] for name in self.calls}
        self.failed_task_ids = set()

    def queue_failure(self, operation, error):
        self.failures[operation].append(error)

    def _before(self, operation):
        self.calls[operation] += 1
        if self.failures[operation]:
            raise self.failures[operation].pop(0)

    def _store(self, fields, record_id=None):
        task_id = fields['Task ID']
        if task_id in self.failed_task_ids:
            raise MockAirtableError('invalid record', 422)
        if record_id is None:
            record_id = f'rec{self.next_id}'
            self.next_id += 1
        self.records[record_id] = dict(fields)
        return {'id': record_id, 'fields': dict(fields)}

    def all(self, **options):
        self._before('all')
        return [
            {'id': record_id, 'fields': dict(fields)}
            for record_id, fields in self.records.items()
        ]

    def batch_create(self, records):
        self._before('batch_create')
        if any(record['Task ID'] in self.failed_task_ids for record in records):
            raise MockAirtableError('invalid batch record', 422)
        return [self._store(record) for record in records]

    def batch_update(self, records):
        self._before('batch_update')
        if any(record['fields']['Task ID'] in self.failed_task_ids for record in records):
            raise MockAirtableError('invalid batch record', 422)
        return [self._store(record['fields'], record['id']) for record in records]

    def create(self, fields):
        self._before('create')
        return self._store(fields)

    def update(self, record_id, fields):
        self._before('update')
        return self._store(fields, record_id)
