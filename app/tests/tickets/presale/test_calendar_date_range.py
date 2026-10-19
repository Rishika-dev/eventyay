from datetime import timedelta

import pytest
from django.utils.timezone import now

from eventyay.base.models import Event, Organizer


OUT_OF_RANGE_MONTHS = [
    'year=0&month=5',
    'year=1&month=1',
    'year=9999&month=12',
    'year=10000&month=1',
    'year=-5&month=1',
    'year=2026&month=13',
    'year=2026&month=0',
]

OUT_OF_RANGE_WEEKS = [
    'year=0&week=5',
    'year=9999&week=52',
    'year=10000&week=1',
    'year=2026&week=99',
    'year=2026&week=-300',
]


@pytest.fixture
def env():
    organizer = Organizer.objects.create(name='MRMCD e.V.', slug='mrmcd')
    event = Event.objects.create(
        organizer=organizer,
        name='MRMCD series',
        slug='series',
        date_from=now() + timedelta(days=10),
        live=True,
        is_public=True,
        has_subevents=True,
    )
    return organizer, event


@pytest.mark.django_db
@pytest.mark.parametrize('query', OUT_OF_RANGE_MONTHS)
@pytest.mark.parametrize('base', ['/mrmcd/', '/mrmcd/widget/product_list', '/mrmcd/series/'])
def test_calendar_falls_back_to_current_month(env, client, base, query):
    r = client.get(f'{base}?style=calendar&{query}')
    assert r.status_code == 200
    if 'widget' in base:
        assert r.json()['date'] == now().date().replace(day=1).isoformat()


@pytest.mark.django_db
@pytest.mark.parametrize('query', OUT_OF_RANGE_WEEKS)
@pytest.mark.parametrize('base', ['/mrmcd/', '/mrmcd/widget/product_list', '/mrmcd/series/'])
def test_week_calendar_falls_back_to_current_week(env, client, base, query):
    r = client.get(f'{base}?style=week&{query}')
    assert r.status_code == 200
