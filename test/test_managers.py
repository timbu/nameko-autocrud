import pytest

from nameko_autocrud.managers import CrudManager


class TestCrudManager:

    def test_invalid_page_size(self):
        manager = CrudManager(None, None)
        with pytest.raises(ValueError) as exc:
            manager.page(0, 1)
        assert 'Invalid page_size (0)' in str(exc)

    def test_invalid_page_num(self):
        manager = CrudManager(None, None)
        with pytest.raises(ValueError) as exc:
            manager.page(1, 0)
        assert 'Invalid page_num (0)' in str(exc)
