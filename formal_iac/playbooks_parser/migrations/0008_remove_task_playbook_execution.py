# Generated by Django 3.0.2 on 2020-05-30 11:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('playbooks_parser', '0007_task_playbook_execution'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='playbook_execution',
        ),
    ]
