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
module: selenium_test
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


# pylint: disable = wrong-import-position
from ansible.module_utils.basic import AnsibleModule  # noqa
from selenium import webdriver  # noqa
from selenium.webdriver.common.keys import Keys  # noqa
from selenium.webdriver.common.by import By  # noqa
from selenium.webdriver.support.ui import WebDriverWait  # noqa
from selenium.webdriver.support import expected_conditions as EC  # noqa
from selenium.common.exceptions import NoSuchElementException  # noqa
from selenium.common.exceptions import TimeoutException  # noqa


class AnsibleSelenium(object):
    """Ansible Selenium Class."""

    def __init__(self, module):
        """Init."""
        self.module = module
        self.args = module.params
        self.arg = lambda: None
        for arg in self.args:
            setattr(self.arg, arg, self.args[arg])

        self.steps_num = len(self.arg.steps) - 1
        self.result = {'changed': False,
                       'failed': False,
                       'results': {
                           'steps': [],
                           'num': self.steps_num
                       }}
        self.browser = self._browser()

        if 'http' not in self.arg.url:
            self.failed('invalid url.')

    def __enter__(self):
        """Enter."""
        self.load()
        return self

    def __exit__(self, type, value, traceback):
        """Exit."""
        # pylint: disable = redefined-builtin
        self.close()

    def load(self):
        """Load website."""
        self.browser.get(self.arg.url)

    def close(self):
        """Close."""
        self.browser.close()

    def _browser(self):
        """Return browser."""
        name = self.arg.browser
        driver = None
        if 'phantomjs' in name:
            driver = self._phantomjs()
        elif 'firefox' in name:
            driver = self._firefox()
        elif 'chrome' in name:
            driver = self._chrome()
        return driver

    def _phantomjs(self):
        """Use PhantomJS browser."""
        service_args = ['--ssl-protocol=any']
        if not self.arg.validate_cert:
            service_args.append('--ignore-ssl-errors=true')
        driver = webdriver.PhantomJS(service_args=service_args)
        driver.set_window_size(self.arg.width, self.arg.height)
        driver.set_page_load_timeout(self.arg.implicit_wait)
        return driver

    def _firefox(self):
        """Use Firefox browser."""
        # pylint: disable = no-self-use
        driver = webdriver.Firefox()
        return driver

    def _chrome(self):
        """Use Chrome browser."""
        # pylint: disable = no-self-use
        driver = webdriver.Chrome()
        return driver

    def failed(self, msg, step=None):
        """Failed."""
        self.result['failed'] = True
        self.result['msg'] = msg
        if step:
            step['error'] = True
            step['msg'] = msg
            when = self.arg.screenshot_when
            if 'all' in when or 'error' in when:
                step['screenshot'] = self.screenshot('failed')
            self.result['results']['steps'].append(step)
        else:
            self.result['results']['screenshot'] = self.screenshot('failed')
        self.module.exit_json(**self.result)

    def screenshot(self, suffix='default'):
        """Screenshot."""
        details = {}
        if 'base64' in self.arg.screenshot_type:
            base64 = self.browser.get_screenshot_as_base64()
            details['base64'] = base64
        elif 'file' in self.arg.screenshot_type:
            path = '%s/%s%s.png' % (self.arg.screenshot_path,
                                    self.arg.screenshot_prefix,
                                    suffix)
            self.browser.get_screenshot_as_file(path)
            details['file'] = path
        return details

    def keys(self, step, step_result):
        """Keys."""
        step_result['keys'] = False
        try:
            keys_method = getattr(self.browser, step['keys']['type'])
            if 'text' in step['keys']:
                value = step['keys']['text']
                keys_method(step['keys']['value']).send_keys(value)
            if 'key' in step['keys']:
                key_type = getattr(Keys, step['keys']['key'])
                keys_method(step['keys']['value']).send_keys(key_type)
        except KeyError:
            self.failed('configuration failure. check syntax.', step_result)
        except AttributeError:
            self.failed('type error. check syntax.', step_result)
        except NoSuchElementException:
            self.failed('no such element.', step_result)
        step_result['keys'] = True
        return step_result

    def click(self, step, step_result):
        """Click."""
        step_result['click'] = False
        try:
            click_method = getattr(self.browser, step['click']['type'])
            click_method(step['click']['text']).click()
        except KeyError:
            self.failed('configuration failure. check syntax.', step_result)
        except AttributeError:
            self.failed('type error. check syntax.', step_result)
        except NoSuchElementException:
            self.failed('no such element.', step_result)
        step_result['click'] = True
        return step_result

    def wait_for(self, step, step_result):
        """Wait for."""
        step_result['wait_for'] = False
        try:
            waitfor_method = getattr(EC, step['wait_for']['method'])
            waitfor_type = getattr(By, step['wait_for']['type'])
            waitfor_text = step['wait_for']['text']
        except KeyError:
            self.failed('configuration failure. check syntax.', step_result)
        except AttributeError:
            self.failed('method or type error. check syntax.', step_result)

        try:
            WebDriverWait(self.browser, self.arg.explicit_wait).until(
                waitfor_method((waitfor_type, waitfor_text))
            )
        except TimeoutException:
            self.failed('failure waiting for element.', step_result)
        step_result['wait_for'] = True
        return step_result

    def asserts(self, step, step_result):
        """Assertions."""
        step_result['assert'] = True
        step_result['assert_results'] = []
        for aidx, item in enumerate(step['assert']):
            step_result['assert_results'].append(False)
            try:
                assert_method = getattr(self.browser, item['type'])
                assert assert_method(item['text'])
            except KeyError:
                self.failed('configuration failure. check syntax.',
                            step_result)
            except NoSuchElementException:
                self.failed('no such element.', step_result)
            step_result['assert_results'][aidx] = True
        step_result['assert'] = True
        return step_result


def main():
    """Main."""
    # pylint: disable = too-many-branches
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

    # initiate module
    with AnsibleSelenium(module) as sel:
        # validate title
        if sel.arg.title in sel.browser.title:
            sel.result['results']['title'] = True
        else:
            sel.result['results']['title'] = False
            sel.failed('title does not match')

        # process each step
        for idx, step in enumerate(sel.arg.steps):
            step_result = {'id': idx,
                           'screenshot': 'no'}
            if 'name' in step:
                step_result['name'] = step['name']

            if 'keys' in step:
                step_result.update(sel.keys(step, step_result))

            if 'click' in step:
                step_result.update(sel.click(step, step_result))

            if 'wait_for' in step:
                step_result.update(sel.wait_for(step, step_result))

            if 'assert' in step:
                step_result.update(sel.asserts(step, step_result))

            if sel.arg.screenshot:
                capture = False
                if 'all' in sel.arg.screenshot_when:
                    capture = True
                elif 'start' in sel.arg.screenshot_when and idx is 0:
                    capture = True
                elif 'end' in sel.arg.screenshot_when and idx is sel.steps_num:
                    capture = True

                if capture:
                    suffix = idx
                    if 'name' in step:
                        suffix = '%s_%s' % (idx, step['name'])
                    step_result['screenshot'] = sel.screenshot(suffix)
            sel.result['results']['steps'].append(step_result)
        module.exit_json(**sel.result)


if __name__ == '__main__':
    main()
