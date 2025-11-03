from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Company, SubCompany


@receiver(post_save, sender=Company)
def create_default_subcompany(sender, instance, created, **kwargs):
    """
    Crée automatiquement une sous-entreprise par défaut lors de la création d'une entreprise
    """
    if created:
        instance.create_default_subcompany()
        print(f"✅ Sous-entreprise par défaut créée pour {instance.name}")


@receiver(post_save, sender=SubCompany)
def update_subcompany_reference(sender, instance, created, **kwargs):
    """
    Met à jour la référence de la sous-entreprise si nécessaire
    """
    if created and not instance.reference:
        instance.reference = instance.generate_unique_reference()
        instance.save()
        print(f"✅ Référence générée pour la sous-entreprise {instance.name}: {instance.reference}")
