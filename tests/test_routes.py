import io
from pathlib import Path
from unittest import mock

import pytest


def test_index(client):
    rs = client.get('/')

    assert rs.status_code == 200
    assert b"Alloza's Cloud" in rs.data
    assert b'folder' in rs.data
    assert b'Files' in rs.data
    assert b'Upload' in rs.data

    assert client.post('/').status_code == 405
    assert client.patch('/').status_code == 405
    assert client.delete('/').status_code == 405
    assert client.put('/').status_code == 405


class TestUpload:
    @pytest.fixture(autouse=True)
    def upload_mocks(self):
        folders = [Path(x) for x in ['folder-1', 'folder-2', 'folder-3']]

        cfg_mock = mock.patch('app.cfg').start()
        file_storage_mock = mock.patch('werkzeug.datastructures.FileStorage.save').start()
        get_folders_mock = mock.patch('app.get_folders', return_value=folders).start()
        log_mock = mock.patch('app.log').start()
        get_user_mock = mock.patch('app.get_user', return_value='user-foo').start()

        cfg_mock.CLOUD_PATH = '/cloud'

        yield cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock

        mock.patch.stopall()

    def test_one_file(self, client, upload_mocks):
        cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock = upload_mocks

        rv = client.post('/upload', data=dict(
            files=[(io.BytesIO(b"this is a test"), 'test.pdf')],
            folder=0, submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 200
        file_storage_mock.assert_called_once_with('/cloud/folder-1/test.pdf')
        assert file_storage_mock.call_count == 1

        rv = client.post('/upload', data=dict(
            files=[(io.BytesIO(b"this is a test"), 'test.rar')],
            folder=2, submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 200
        file_storage_mock.assert_called_with('/cloud/folder-3/test.rar')
        assert file_storage_mock.call_count == 2

    def test_multiple_files(self, client, upload_mocks):
        cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock = upload_mocks

        file_storage_mock.reset_mock()
        rv = client.post('/upload', data=dict(
            files=[
                (io.BytesIO(b"this is a test"), 'test-1.py'),
                (io.BytesIO(b"this is a test"), 'test-2.py'),
                (io.BytesIO(b"this is a test"), 'test-3.py')
            ],
            folder=2, submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 200
        file_storage_mock.assert_has_calls(
            [mock.call('/cloud/folder-3/test-1.py'), mock.call('/cloud/folder-3/test-2.py'),
             mock.call('/cloud/folder-3/test-3.py')])

        assert file_storage_mock.call_count == 3

    def test_no_files(self, client, upload_mocks):
        cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock = upload_mocks

        file_storage_mock.reset_mock()
        rv = client.post('/upload', data=dict(
            files=[],
            folder=2, submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 400
        assert b'No files supplied' in rv.data
        file_storage_mock.assert_not_called()

    def test_folder_as_str(self, client, upload_mocks):
        cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock = upload_mocks

        rv = client.post('/upload', data=dict(
            files=[(io.BytesIO(b"this is a test"), 'whatever.rar')],
            folder='2', submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 200
        file_storage_mock.assert_called_once_with('/cloud/folder-3/whatever.rar')

    def test_no_folder(self, client, upload_mocks):
        cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock = upload_mocks

        rv = client.post('/upload', data=dict(
            files=[(io.BytesIO(b"this is a test"), 'whatever.pdf')],
            submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 400
        assert b'No folder supplied' in rv.data
        file_storage_mock.assert_not_called()

    def test_type_invalid_folder(self, client, upload_mocks):
        cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock = upload_mocks

        rv = client.post('/upload', data=dict(
            files=[(io.BytesIO(b"this is a test"), 'whatever.rar')],
            folder='-', submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 400
        assert b'No folder supplied or an invalid folder was supplied' in rv.data
        file_storage_mock.assert_not_called()

    def test_index_invalid_folder(self, client, upload_mocks):
        cfg_mock, file_storage_mock, get_folders_mock, log_mock, get_user_mock = upload_mocks

        rv = client.post('/upload', data=dict(
            files=[(io.BytesIO(b"this is a test"), 'whatever.rar')],
            folder=65, submit='Upload'
        ), follow_redirects=True)

        assert rv.status_code == 400
        assert b'Invalid index folder' in rv.data
        file_storage_mock.assert_not_called()
