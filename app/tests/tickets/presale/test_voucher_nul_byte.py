from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.utils.timezone import now
from django_scopes import scopes_disabled

from eventyay.base.models import Event, Order, Organizer, Product, Quota, Voucher
from eventyay.base.payment import GiftCardPayment
from eventyay.base.services.cart import CartError, CartManager, error_messages


NUL_CODES = ['\x00', 'ABC\x00DEF']


@pytest.fixture
@scopes_disabled()
def event():
    organizer = Organizer.objects.create(name='Dummy', slug='dummy')
    event = Event.objects.create(
        organizer=organizer,
        name='Dummy',
        slug='dummy',
        date_from=now() + timedelta(days=30),
        live=True,
        tickets_published=True,
    )
    product = Product.objects.create(event=event, name='Ticket', default_price=10)
    quota = Quota.objects.create(event=event, name='Tickets', size=10)
    quota.products.add(product)
    Voucher.objects.create(event=event, code='ABCDEF', product=product)
    return event


@pytest.mark.django_db
@pytest.mark.parametrize('code', NUL_CODES)
def test_redeem_rejects_code_with_nul_byte(client, event, code):
    response = client.get('/dummy/dummy/redeem/', {'voucher': code}, follow=True)
    assert response.status_code == 200
    assert str(error_messages['voucher_invalid']) in response.content.decode()


@pytest.mark.django_db
def test_redeem_still_accepts_valid_code(client, event):
    response = client.get('/dummy/dummy/redeem/', {'voucher': 'ABCDEF'})
    assert response.status_code == 200
    assert str(error_messages['voucher_invalid']) not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize('code', NUL_CODES)
def test_widget_rejects_code_with_nul_byte(client, event, code):
    response = client.get('/dummy/dummy/widget/product_list', {'voucher': code})
    assert response.status_code == 200
    assert response.json()['error'] == str(error_messages['voucher_invalid'])


@pytest.mark.django_db
@pytest.mark.parametrize('code', NUL_CODES)
@scopes_disabled()
def test_cart_add_rejects_code_with_nul_byte(event, code):
    product = event.products.get()
    cm = CartManager(event=event, cart_id='dummy')
    with pytest.raises(CartError, match=str(error_messages['voucher_invalid'])):
        cm.add_new_products([{'product': product.pk, 'variation': None, 'count': 1, 'voucher': code}])


@pytest.mark.django_db
@pytest.mark.parametrize('code', NUL_CODES)
@scopes_disabled()
def test_cart_apply_voucher_rejects_code_with_nul_byte(event, code):
    cm = CartManager(event=event, cart_id='dummy')
    with pytest.raises(CartError, match=str(error_messages['voucher_invalid'])):
        cm.apply_voucher(code)


def giftcard_request(event, code):
    request = RequestFactory().post('/dummy/dummy/checkout/payment/', {'giftcard': code})
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)
    request.event = event
    request.organizer = event.organizer
    request.resolver_match = None
    return request


@pytest.mark.django_db
@pytest.mark.parametrize('code', NUL_CODES)
@scopes_disabled()
def test_giftcard_checkout_rejects_code_with_nul_byte(event, code):
    request = giftcard_request(event, code)
    assert GiftCardPayment(event).checkout_prepare(request, {}) is None
    assert [str(m) for m in get_messages(request)] == ['This gift card is not known.']


@pytest.mark.django_db
@pytest.mark.parametrize('code', NUL_CODES)
@scopes_disabled()
def test_giftcard_payment_rejects_code_with_nul_byte(event, code):
    order = Order.objects.create(
        code='FOO',
        event=event,
        email='dummy@dummy.test',
        status=Order.STATUS_PENDING,
        datetime=now(),
        expires=now() + timedelta(days=10),
        total=10,
    )
    payment = order.payments.create(amount=10, provider='giftcard')
    request = giftcard_request(event, code)
    assert GiftCardPayment(event).payment_prepare(request, payment) is None
    assert [str(m) for m in get_messages(request)] == ['This gift card is not known.']


@pytest.mark.django_db
@pytest.mark.parametrize('code', NUL_CODES)
def test_event_index_with_dates_ignores_code_with_nul_byte(client, event, code):
    with scopes_disabled():
        event.has_subevents = True
        event.save()
        event.subevents.create(name='Day 1', date_from=now() + timedelta(days=30), active=True)
    response = client.get('/dummy/dummy/', {'voucher': code})
    assert response.status_code == 200
    assert 'Day 1' in response.content.decode()
