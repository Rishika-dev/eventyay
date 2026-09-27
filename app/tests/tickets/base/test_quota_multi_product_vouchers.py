from datetime import timedelta

import pytest
from django.utils.timezone import now
from django_scopes import scopes_disabled

from eventyay.base.models import Event, Organizer, Product, Quota, Voucher
from eventyay.base.services.quotas import QuotaAvailability


@pytest.fixture
@scopes_disabled()
def event():
    organizer = Organizer.objects.create(name='Dummy', slug='dummy')
    return Event.objects.create(
        organizer=organizer,
        name='Dummy',
        slug='dummy',
        date_from=now() + timedelta(days=30),
        date_to=now() + timedelta(days=31),
    )


@pytest.fixture
@scopes_disabled()
def products(event):
    ticket = Product.objects.create(event=event, name='Ticket', default_price=10)
    pass_ = Product.objects.create(event=event, name='Pass', default_price=0)
    return ticket, pass_


def availability(*quotas):
    qa = QuotaAvailability(full_results=True)
    qa.queue(*quotas)
    qa.compute(now_dt=now())
    return {q: qa.results[q][1] for q in quotas}


def multi_product_voucher(event, products, **kwargs):
    voucher = Voucher.objects.create(event=event, **{'block_quota': True, 'max_usages': 3, **kwargs})
    voucher.limit_products.set(products)
    return voucher


@pytest.mark.django_db
@scopes_disabled()
def test_blocks_quota_of_every_limited_product(event, products):
    ticket, pass_ = products
    ticket_quota = Quota.objects.create(event=event, name='Tickets', size=10)
    ticket_quota.products.add(ticket)
    pass_quota = Quota.objects.create(event=event, name='Passes', size=2)
    pass_quota.products.add(pass_)

    multi_product_voucher(event, [ticket, pass_], max_usages=1)

    assert availability(ticket_quota, pass_quota) == {ticket_quota: 9, pass_quota: 1}


@pytest.mark.django_db
@scopes_disabled()
def test_blocks_shared_quota_once_per_voucher(event, products):
    quota = Quota.objects.create(event=event, name='Shared', size=10)
    quota.products.add(*products)

    multi_product_voucher(event, products, max_usages=3)

    assert availability(quota) == {quota: 7}


@pytest.mark.django_db
@scopes_disabled()
def test_only_unredeemed_usages_of_valid_blocking_vouchers_count(event, products):
    quota = Quota.objects.create(event=event, name='Shared', size=10)
    quota.products.add(*products)

    multi_product_voucher(event, products, max_usages=3, redeemed=2)
    multi_product_voucher(event, products, max_usages=3, valid_until=now() - timedelta(days=1))
    multi_product_voucher(event, products, max_usages=3, block_quota=False)

    assert availability(quota) == {quota: 9}


@pytest.mark.django_db
@scopes_disabled()
def test_blocks_quota_of_limited_variation_only(event):
    shirt = Product.objects.create(event=event, name='Shirt', default_price=20)
    small = shirt.variations.create(value='S')
    large = shirt.variations.create(value='L')
    small_quota = Quota.objects.create(event=event, name='Small', size=5)
    small_quota.products.add(shirt)
    small_quota.variations.add(small)
    large_quota = Quota.objects.create(event=event, name='Large', size=5)
    large_quota.products.add(shirt)
    large_quota.variations.add(large)

    voucher = multi_product_voucher(event, [shirt], max_usages=2)
    voucher.limit_variations.set([small])

    assert availability(small_quota, large_quota) == {small_quota: 3, large_quota: 5}
