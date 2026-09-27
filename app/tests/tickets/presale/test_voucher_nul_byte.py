from datetime import timedelta

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from eventyay.base.models import Event, Organizer, Product, Quota, Voucher
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
