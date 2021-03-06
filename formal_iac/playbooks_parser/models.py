from django.db import models


class Vulnerability(models.Model):
    cve = models.CharField(max_length=200)
    cve_url = models.URLField()
    impact = models.CharField(max_length=50)

    def __str__(self):
        return self.cve


class Package(models.Model):
    package_name = models.CharField(max_length=200)
    set_of_vulnerabilities = models.ManyToManyField(Vulnerability)

    def __str__(self):
        return self.package_name


class State(models.Model):
    state_name = models.CharField(max_length=200)
    set_of_packages = models.ManyToManyField(Package)

    def __str__(self):
        return self.state_name


class PlaybookExecution(models.Model):
    execution_id = models.CharField(max_length=200)
    list_of_states = models.ManyToManyField(State)

    def __str__(self):
        return self.execution_id


class Task(models.Model):
    task_name = models.CharField(max_length=200)
    task_module = models.CharField(max_length=200)
    # module_arguments should be a list of strings for each option
    module_options = models.CharField(max_length=200)
    # module_arguments should be a list of strings for each argument
    module_arguments = models.CharField(max_length=200)

    def __str__(self):
        return self.task_name


class Playbook(models.Model):
    playbook_name = models.CharField(max_length=200)
    # Text Field instead of Charfield as it is potentially a huge amount of characters
    playbook_content = models.TextField()
    list_of_tasks = models.ManyToManyField(Task)

    def __str__(self):
        return self.playbook_name
