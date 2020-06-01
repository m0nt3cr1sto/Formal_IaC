from .models import Package, Playbook, PlaybookExecution, State, Task, Vulnerability
from formal_iac import settings

from bs4 import BeautifulSoup
import requests
import yaml
from datetime import datetime


def parse_playbook_aux(playbook_content: str):
    list_of_tasks_dicts = yaml.load(playbook_content)[0]['tasks']
    return list_of_tasks_dicts


# INPUT: Playbook Content
# OUTPUT: List of the tasks it contains
def create_tasks(playbook_content: str):
    list_of_tasks = parse_playbook_aux(playbook_content)
    created_tasks = []
    for task in list_of_tasks:
        task_created = Task(task_name=task['name'] + " " + str(datetime.now()), task_module=list(task)[1],
                            module_arguments=task['yum']['name'], module_options=task['yum']['state'])
        task_created.save()
        created_tasks.append(task_created)
    return created_tasks


# Auxiliary function to create a playbook from an uploaded file
# Will be called only when a playbook is uploaded
def create_playbook(uploaded_content):
    playbook_content = ""
    for line in uploaded_content:
        playbook_content = playbook_content + line.decode("utf-8")
    list_of_tasks = create_tasks(playbook_content)
    playbook_created = Playbook(playbook_name="Uploaded_playbook " + str(datetime.now()),
                                playbook_content=playbook_content)
    playbook_created.save()
    playbook_created.list_of_tasks.set(list_of_tasks)
    playbook_created.save()
    return playbook_created


# Auxiliary function to create the states the execution of a playbook will generate
def create_playbook_execution(playbook_to_analyze):
    pl_name = playbook_to_analyze.playbook_name
    state_counter = 0
    execution_created = PlaybookExecution(execution_id=pl_name + " analysis")
    execution_created.save()
    initial_state = State(state_name=pl_name + " state " + str(state_counter))
    initial_state.save()
    execution_created.list_of_states.add(initial_state)
    previous_state = initial_state
    # For each task in the playbook's list of tasks, create a state
    for task in playbook_to_analyze.list_of_tasks.all():
        state_counter += 1
        new_state_name = pl_name + " state " + str(state_counter)
        new_state = State(state_name=new_state_name)
        new_state.save()
        new_state.set_of_packages.set(previous_state.set_of_packages.all())
        # The new state is the previous one with one more package
        if task.module_options == 'present':
            # The package exists, retrieve it
            if Package.objects.filter(package_name=task.module_arguments):
                package_to_install = Package.objects.filter(package_name=task.module_arguments)[0]
            # The package does not exists, create it
            else:
                package_to_install = Package(package_name=task.module_arguments)
                package_to_install.save()
                package_vulnerabilities = check_vuln(package_to_install)
                package_to_install.set_of_vulnerabilities.set(package_vulnerabilities)
            new_state.set_of_packages.add(package_to_install)
        elif task.module_options == 'absent':
            # If the package exists -> it has been installed or part of the initial state -> Remove it
            if Package.objects.filter(package_name=task.module_arguments):
                package_to_remove = Package.objects.filter(package_name=task.module_arguments)[0]
                new_state.set_of_packages.remove(package_to_remove)
            # Else the package is not installed so do nothing
        execution_created.list_of_states.add(new_state)
        previous_state = new_state
    return execution_created


def create_dict_vuln_packages_aux():
    soup = BeautifulSoup(requests.get(settings.CANONICAL_PACKAGE_INFO_URL).text, "html.parser")
    table_of_packages = soup.find(id='cves').tbody.find_all('tr')
    dict_of_vulnerable_packages = {}
    # Dict structure
    # Entries where the package name is the key
    # The values is a list of tuples CVE's (including their href) + Impact
    for table_row in table_of_packages:
        if 'low' in table_row['class'] or 'high' in table_row['class']:
            package_name = table_row.find_all('td', class_='pkg')[0].a.text
            cve_name = table_row.find_all('td', class_='cve')[0].a.text
            cve_url = "https://nvd.nist.gov/vuln/detail/" + cve_name
            # cve_url = "https://cve.mitre.org/cgi-bin/cvename.cgi?name=" + cve_name
            if package_name in dict_of_vulnerable_packages.keys():
                dict_of_vulnerable_packages[package_name].append(
                    (cve_name, cve_url, table_row['class'][0]))
            else:
                dict_of_vulnerable_packages[package_name] = [
                    (cve_name, cve_url, table_row['class'][0])]
    return dict_of_vulnerable_packages


# INPUT: A package
# OUTPUT: Either a list of vulnerability objects or an empty list
def check_vuln(package):
    vulnerabilities_dict = create_dict_vuln_packages_aux()
    package_vulnerabilities = []
    # TODO create vulnerability DBs rather than retrieving it for every task
    if package.package_name in vulnerabilities_dict.keys():
        for vulnerability in vulnerabilities_dict[package.package_name]:
            new_vuln = Vulnerability(cve=vulnerability[0], cve_url=vulnerability[1], impact=vulnerability[2])
            new_vuln.save()
            package_vulnerabilities.append(new_vuln)
    return package_vulnerabilities


# INPUT: a list of dictionaries specifying tasks on a playbook (in this case package installations)
# OUTPUT: a list of tuples where first element is the package name and the second element is the available CVEs
# TODO instead of analyze a playbook analyze a playbook execution, iterate over the states
# IDEA: A list of tuples (state_n, warnings_of_state_n)
def analyse_vuln_packages(playbook):
    playbook_warnings = []
    # Construct source of vulnerable packages
    vuln_packages = create_dict_vuln_packages_aux()
    for task in playbook.list_of_tasks.all():
        package_name = task.module_arguments
        if package_name in vuln_packages.keys():
            playbook_warnings.append((package_name, vuln_packages[package_name]))
    return playbook_warnings

