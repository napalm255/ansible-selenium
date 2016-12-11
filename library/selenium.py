#!/usr/bin/env python
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

"""Ansible Selenium Module."""

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
from ansible.module_utils._text import to_native
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


def main():
    """Main."""
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type='str', required=True),
            browser=dict(type='str', default='phantomjs',
                         choices=['phantomjs', 'firefox', 'chrome']),
            width=dict(type='int', default=1024),
            height=dict(type='int', default=768),
            title=dict(type='str'),
            screenshot=dict(type='bool', default=False),
            screenshot_when=dict(type='list', default=['error']),
            screenshot_type=dict(type='str', default='base64',
                                 choices=['file', 'base64']),
            screenshot_path=dict(type='str', default='/tmp'),
            screenshot_prefix=dict(type='str', default='selenium_'),
            steps=dict(type='list', required=True),
            explicit_wait=dict(type='int', default=2),
            implicit_wait=dict(type='int', default=20),
            validate_cert=dict(type='bool', default=True),
        ),
        supports_check_mode=True
    )

    args = module.params
    result = {'changed': False, 'failed': False}

    def failed(msg, step=None):
        """Failed."""
        result['failed'] = True
        result['msg'] = msg
        if step:
            step['error'] = True
            when = args['screenshot_when']
            if 'all' in when or 'error' in when:
                step['screenshot'] = screenshot('failed')
            steps.append(step)
            result['steps'] = steps
        else:
            result['screenshot'] = screenshot('failed')
        module.exit_json(**result)

    def screenshot(suffix='default'):
        """Screenshot."""
        details = {}
        if 'base64' in args['screenshot_type']:
            base64 = browser.get_screenshot_as_base64()
            details['base64'] = base64
        elif 'file' in args['screenshot_type']:
            path = '%s/%s%s.png' % (args['screenshot_path'],
                                    args['screenshot_prefix'],
                                    suffix)
            browser.get_screenshot_as_file(path)
            details['file'] = path
        return details

    def load_browser(name=args['browser']):
        """Browser."""
        if 'phantomjs' in name:
            service_args = ['--ssl-protocol=any']
            if not args['validate_cert']:
                service_args.append('--ignore-ssl-errors=true')
            browser = webdriver.PhantomJS(service_args=service_args)
            browser.set_window_size(args['width'], args['height'])
            browser.set_page_load_timeout(args['implicit_wait'])
        if 'firefox' in name:
            msg = 'firefox browser not supported at this time.'
            failed(msg)
        if 'chrome' in name:
            msg = 'chrome browser not supported at this time.'
            failed(msg)
        return browser

    # validate url
    if 'http' not in args['url']:
        failed('invalid url')

    # load browser
    browser = load_browser()

    # load website
    browser.get(args['url'])

    # validate initial title
    if args['title']:
        if args['title'] in browser.title:
            result['title'] = True
        else:
            failed('title does not match')

    # process each step
    steps = []
    for idx, step in enumerate(args['steps']):
        idx_max = len(args['steps']) - 1
        step_result = {'id': idx, 'screenshot': 'no'}
        if 'click' in step['step']:
            step_result['click'] = False
            try:
                click_method = getattr(browser, step['step']['click']['type'])
                click_method(step['step']['click']['text']).click()
            except KeyError:
                failed('configuration failure. check syntax.', step_result)
            except AttributeError:
                failed('type error. check syntax.', step_result)
            except NoSuchElementException:
                failed('no such element.', step_result)
            step_result['click'] = True

        if 'wait_for' in step['step']:
            step_result['wait_for'] = False
            try:
                waitfor_type = getattr(By, step['step']['wait_for']['type'])
                waitfor_text = step['step']['wait_for']['text']
            except KeyError:
                failed('configuration failure. check syntax.', step_result)
            except AttributeError:
                failed('type error. check syntax.', step_result)

            try:
                WebDriverWait(browser, args['explicit_wait']).until(
                    EC.presence_of_element_located((waitfor_type,
                                                    waitfor_text))
                )
            except TimeoutException:
                failed('failure waiting for element.', step_result)
            step_result['wait_for'] = True

        if 'assert' in step['step']:
            step_result['assert'] = False
            step_result['assert_results'] = []
            for aidx, item in enumerate(step['step']['assert']):
                step_result['assert_results'].append(False)
                try:
                    assert_method = getattr(browser, item['type'])
                    assert assert_method(item['text'])
                except KeyError:
                    failed('configuration failure. check syntax.', step_result)
                except NoSuchElementException:
                    failed('no such element.', step_result)
                step_result['assert_results'][aidx] = True
            step_result['assert'] = True

        suffix = idx
        if 'name' in step['step']:
            suffix = '%s_%s' % (idx, step['step']['name'])
            step_result['name'] = step['step']['name']

        if args['screenshot']:
            capture = False
            if 'all' in args['screenshot_when']:
                capture = True
            elif 'start' in args['screenshot_when'] and idx is 0:
                capture = True
            elif 'end' in args['screenshot_when'] and idx is idx_max:
                capture = True

            if capture:
                step_result['screenshot'] = screenshot(suffix)
        steps.append(step_result)
    browser.close()
    result['results'] = steps
    module.exit_json(**result)


if __name__ == '__main__':
    main()
