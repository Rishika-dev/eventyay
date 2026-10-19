import re

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django_scopes import scopes_disabled

from eventyay.base.models import LogEntry


def user_option(response, user):
    match = re.search(rf'<option value="{user.pk}"[^>]*>', response.content.decode(), re.S)
    assert match, f'no option for user {user.pk}'
    return match.group(0)


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
@pytest.mark.parametrize('page', ['event', 'organizer'])
def test_log_user_filter_keeps_the_selected_team_member(organizer_client, organizer, event, user, page):
    if page == 'event':
        obj = event
        url = reverse('control:event.log', kwargs={'organizer': organizer.slug, 'event': event.slug})
    else:
        obj = organizer
        url = reverse('control:organizer.log', kwargs={'organizer': organizer.slug})

    with scopes_disabled():
        LogEntry.objects.create(
            event=event if page == 'event' else None,
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.pk,
            user=user,
            action_type='test.user.filter',
        )

    response = organizer_client.get(url)
    assert response.status_code == 200
    assert 'selected' not in user_option(response, user)

    response = organizer_client.get(url, {'user': user.pk})
    assert response.status_code == 200
    assert 'selected="selected"' in user_option(response, user)
