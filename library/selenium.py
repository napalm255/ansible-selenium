#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Brad Gibson <napalm255@gmail.com>
#
# This file is a 3rd Party module for Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: selenium
author: "Brad Gibson"
version_added: "2.3"
short_description: Run selenium tests
requirements: [ phantomjs, firefox, chrome ]
description:
    - Run selenium tests against url.
options:
    url:
        required: true
        description:
            - URL to run selenium tests against.
'''

EXAMPLES = '''
# run basic check against given url
- selenium: url=http://www.python.org
'''


from ansible.module_utils.basic import AnsibleModule
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ansible.module_utils._text import to_native


def main():
    """Main."""
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(required=True, type='str'),
            title=dict(type='str'),
            login=dict(type='dict', required=True),
            steps=dict(type='list', required=True),
        ),
        supports_check_mode=True
    )

    args = module.params

    result = {}
    try:
        browser = webdriver.PhantomJS()
        browser.set_window_size(1024, 768)
        browser.get(args['url'])
        if args['title']:
            assert args['title'] in browser.title
            result['title'] = True

        for step in args['steps']:
            step_method = getattr(browser, step['step']['click']['type'])
            step_method(step['step']['click']['text']).click()
            elem_type = getattr(By, step['step']['wait_for']['type'])
            elem_text = step['step']['wait_for']['text']
            WebDriverWait(browser, 2).until(
                EC.presence_of_element_located((elem_type, elem_text))
            )
            result['test'] = str(browser.get_screenshot_as_base64())
            browser.get_screenshot_as_file('/tmp/testing.png')
        browser.close()
        result['changed'] = False
    except AssertionError:
        result['failed'] = True
        result['msg'] = 'error while testing url'

    module.exit_json(**result)


if __name__ == '__main__':
    main()
