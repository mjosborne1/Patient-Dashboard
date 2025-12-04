#!/usr/bin/env python3
"""Test group task query"""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup FHIR server and auth
server_url = os.getenv('FHIR_SERVER', 'https://smile.sparked-fhir.com/ereq/fhir/DEFAULT')
username = os.getenv('FHIR_USERNAME', 'placer')
password = os.getenv('FHIR_PASSWORD', '')

print(f'Using server: {server_url}')
print(f'Username: {username}')

# Test the group tasks query - handle both tag systems
url = f'{server_url}/Task?_tag=http://terminology.hl7.org.au/CodeSystem/resource-tag|fulfilment-task-group,http://hl7.org.au/fhir/ereq/CodeSystem/au-erequesting-task-tag|fulfilment-task-group'
print(f'Query URL: {url}')

try:
    response = requests.get(url, auth=(username, password), timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        tasks = data.get('entry', [])
        print(f'\nFound {len(tasks)} group tasks')
        
        # Look for task 18156 specifically
        found_task = None
        status_counts = {}
        task_list = []
        
        for entry in tasks:
            resource = entry.get('resource', {})
            task_id = resource.get('id', 'unknown')
            status = resource.get('status', 'unknown')
            
            # Count statuses
            status_counts[status] = status_counts.get(status, 0) + 1
            task_list.append((task_id, status))
            
            if task_id == '18156':
                found_task = resource
                print(f'\n*** FOUND TASK 18156: status = "{status}" ***')
                print(f'Full resource ID: {resource.get("id")}')
                print(f'Status: {resource.get("status")}')
                print(f'Business Status: {resource.get("businessStatus", "None")}')
        
        if not found_task:
            print('\n*** Task 18156 NOT found in group tasks ***')
            print('Available task IDs and statuses:')
            for task_id, status in task_list:
                print(f'  - Task {task_id}: {status}')
        
        print(f'\nStatus counts found: {status_counts}')
        
        # Test direct access to task 18156
        print(f'\n--- Testing direct access to Task/18156 ---')
        direct_url = f'{server_url}/Task/18156'
        direct_response = requests.get(direct_url, auth=(username, password), timeout=10)
        if direct_response.status_code == 200:
            task_resource = direct_response.json()
            print(f'Direct access SUCCESS')
            print(f'Task ID: {task_resource.get("id")}')
            print(f'Status: {task_resource.get("status")}')
            print(f'Meta tags: {task_resource.get("meta", {}).get("tag", [])}')
        else:
            print(f'Direct access FAILED: {direct_response.status_code}')
            
    else:
        print(f'Query failed with status {response.status_code}')
        print(f'Response: {response.text[:500]}...')
        
except Exception as e:
    print(f'Error: {e}')
