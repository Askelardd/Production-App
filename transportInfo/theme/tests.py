from django.test import TestCase # type: ignore
from django.contrib.auth.models import User # pyright: ignore[reportMissingModuleSource]
from theme.models import Products

class ProdutoTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='joao',
            password='senha123',
            first_name='João'
        )

    def test_criar_produto(self):
        produto = Products.objects.create(
            order_Nmber=100,
            box_Nmber=10,
            task='Montagem',
            qnt=5,
            edit_by=self.user
        )

        self.assertEqual(Products.objects.count(), 1)
        self.assertEqual(produto.edit_by.username, 'joao')
