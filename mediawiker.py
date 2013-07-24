#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
pythonver = sys.version_info[0]

if pythonver >= 3:
    from . import mwclient
else:
    import mwclient
import webbrowser
import urllib
from os.path import splitext, basename
from re import sub, findall
import sublime
import sublime_plugin
#https://github.com/wbond/sublime_package_control/wiki/Sublime-Text-3-Compatible-Packages
#http://www.sublimetext.com/docs/2/api_reference.html
#http://www.sublimetext.com/docs/3/api_reference.html
#sublime.message_dialog

CATEGORY_NAMESPACE = 14  # category namespace number
IMAGE_NAMESPACE = 6  # image namespace number
TEMPLATE_NAMESPACE = 10  # template namespace number


def mw_get_setting(key, default_value=None):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    return settings.get(key, default_value)


def mw_set_setting(key, value):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('Mediawiker.sublime-settings')


def mw_get_connect(password=''):
    #TODO: need tests. https???
    site_name_active = mw_get_setting('mediawiki_site_active')
    site_list = mw_get_setting('mediawiki_site')
    site = site_list[site_name_active]['host']
    path = site_list[site_name_active]['path']
    username = site_list[site_name_active]['username']
    domain = site_list[site_name_active]['domain']
    proxy_host = ''
    if 'proxy_host' in site_list[site_name_active]:
        proxy_host = site_list[site_name_active]['proxy_host']
    is_https = True if 'https' in site_list[site_name_active] and site_list[site_name_active]['https'] else False
    if is_https:
        sublime.status_message('Trying to get https connection to https://%s' % site)
    addr = site if not is_https else ('https', site)
    if proxy_host:
        #proxy_host format is host:port, if only host defined, 80 will be used
        addr = proxy_host if not is_https else ('https', proxy_host)
        proto = 'https' if is_https else 'http'
        path = '%s://%s%s' % (proto, site, path)
        sublime.message_dialog('Connection with proxy: %s %s' % (addr, path))
    sitecon = mwclient.Site(addr, path)
    # if login is not empty - auth required
    if username:
        try:
            sitecon.login(username=username, password=password, domain=domain)
            sublime.status_message('Logon successfully.')
        except mwclient.LoginError as e:
            sublime.status_message('Login failed: %s' % e[1]['result'])
            return
    else:
        sublime.status_message('Connection without authorization')
    return sitecon


def mw_get_page_text(site, title):
    denied_message = 'You have not rights to edit this page. Click OK button to view its source.'
    page = site.Pages[title]
    if page.can('edit'):
        return True, page.edit()
    else:
        if sublime.ok_cancel_dialog(denied_message):
            return False, page.edit()
        else:
            return False, ''


def mw_strunquote(string_value):
    if pythonver >= 3:
        return urllib.parse.unquote(string_value)
    else:
        return urllib.unquote(string_value.encode('ascii')).decode('utf-8')


def mw_strquote(string_value):
    if pythonver >= 3:
        return urllib.parse.quote(string_value)
    else:
        return urllib.quote(string_value.encode('utf-8'))


def mw_pagename_clear(pagename):
    """ Return clear pagename if page-url was set instead of.."""
    site_name_active = mw_get_setting('mediawiki_site_active')
    site_list = mw_get_setting('mediawiki_site')
    site = site_list[site_name_active]['host']
    pagepath = site_list[site_name_active]['pagepath']
    try:
        pagename = mw_strunquote(pagename)
    except UnicodeEncodeError:
        #return pagename
        pass
    except Exception:
        #return pagename
        pass

    if site in pagename:
        pagename = sub(r'(https?://)?%s%s' % (site, pagepath), '', pagename)

    sublime.status_message('Page name was cleared.')
    return pagename


def mw_save_mypages(title):
    #for wiki '_' and ' ' are equal in page name
    title = title.replace('_', ' ')
    pagelist_maxsize = mw_get_setting('mediawiker_pagelist_maxsize')
    site_name_active = mw_get_setting('mediawiki_site_active')
    mediawiker_pagelist = mw_get_setting('mediawiker_pagelist', {})

    if site_name_active not in mediawiker_pagelist:
        mediawiker_pagelist[site_name_active] = []

    my_pages = mediawiker_pagelist[site_name_active]

    if my_pages:
        while len(my_pages) >= pagelist_maxsize:
            my_pages.pop(0)

        if title in my_pages:
            #for sorting
            my_pages.remove(title)
    my_pages.append(title)
    mw_set_setting('mediawiker_pagelist', mediawiker_pagelist)


def mw_get_title():
    ''' returns page title of active tab from view_name or from file_name'''

    view_name = sublime.active_window().active_view().name()
    if view_name:
        return view_name
    else:
        #haven't view.name, try to get from view.file_name (without extension)
        file_name = sublime.active_window().active_view().file_name()
        if file_name:
            wiki_extensions = mw_get_setting('mediawiker_files_extension')
            title, ext = splitext(basename(file_name))
            if ext[1:] in wiki_extensions and title:
                return title
            else:
                sublime.status_message('Anauthorized file extension for mediawiki publishing. Check your configuration for correct extensions.')
                return ''
    return ''


def mw_get_hlevel(header_string, substring):
    return int(header_string.count(substring) / 2)


def mw_get_category(category_full_name):
    ''' From full category name like "Category:Name" return tuple (Category, Name) '''
    if ':' in category_full_name:
        return category_full_name.split(':')
    else:
        return 'Category', category_full_name


def mw_get_page_url(page_name=''):
    site_name_active = mw_get_setting('mediawiki_site_active')
    site_list = mw_get_setting('mediawiki_site')
    site = site_list[site_name_active]["host"]

    is_https = False
    if 'https' in site_list[site_name_active]:
        is_https = site_list[site_name_active]["https"]

    proto = 'https' if is_https else 'http'
    pagepath = site_list[site_name_active]["pagepath"]
    if not page_name:
        page_name = mw_strquote(mw_get_title())
    if page_name:
        return '%s://%s%s%s' % (proto, site, pagepath, page_name)
    else:
        return ''


class MediawikerInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, position, text):
        self.view.insert(edit, position, text)


class MediawikerPageCommand(sublime_plugin.WindowCommand):
    '''prepare all actions with wiki'''

    action = ''
    is_inputfixed = False
    run_in_new_window = False

    def run(self, action, title=''):
        self.action = action

        if self.action == 'mediawiker_show_page':
            if mw_get_setting('mediawiker_newtab_ongetpage'):
                self.run_in_new_window = True

            if not title:
                pagename_default = ''
                #use clipboard or selected text for page name
                if bool(mw_get_setting('mediawiker_clipboard_as_defaultpagename')):
                    pagename_default = sublime.get_clipboard().strip()
                if not pagename_default:
                    selection = self.window.active_view().sel()
                    for selreg in selection:
                        pagename_default = self.window.active_view().substr(selreg).strip()
                        break
                self.window.show_input_panel('Wiki page name:', mw_pagename_clear(pagename_default), self.on_done, self.on_change, None)
            else:
                self.on_done(title)
        elif self.action == 'mediawiker_reopen_page':
            #get page name
            if not title:
                title = mw_get_title()
            self.action = 'mediawiker_show_page'
            self.on_done(title)
        elif self.action in ('mediawiker_publish_page', 'mediawiker_add_category', 'mediawiker_category_list', 'mediawiker_search_string_list', 'mediawiker_add_image', 'mediawiker_add_template'):
            self.on_done('')

    def on_change(self, title):
        if title:
            pagename_cleared = mw_pagename_clear(title)
            if title != pagename_cleared:
                self.window.show_input_panel('Wiki page name:', pagename_cleared, self.on_done, self.on_change, None)

    def on_done(self, title):
        if self.run_in_new_window:
            sublime.active_window().new_file()
            self.run_in_new_window = False
        try:
            if title:
                title = mw_pagename_clear(title)
            self.window.run_command("mediawiker_validate_connection_params", {"title": title, "action": self.action})
        except ValueError as e:
            sublime.message_dialog(e)


class MediawikerOpenPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_show_page"})


class MediawikerReopenPageCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_reopen_page"})


class MediawikerPostPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Publish page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_publish_page"})


class MediawikerSetCategoryCommand(sublime_plugin.WindowCommand):
    ''' alias to Add category command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_category"})


class MediawikerInsertImageCommand(sublime_plugin.WindowCommand):
    ''' alias to Add image command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_image"})


class MediawikerInsertTemplateCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_template"})


class MediawikerCategoryTreeCommand(sublime_plugin.WindowCommand):
    ''' alias to Category list command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_category_list"})


class MediawikerSearchStringCommand(sublime_plugin.WindowCommand):
    ''' alias to Search string list command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_search_string_list"})


class MediawikerPageListCommand(sublime_plugin.WindowCommand):
    my_pages = []

    def run(self):
        site_name_active = mw_get_setting('mediawiki_site_active')
        mediawiker_pagelist = mw_get_setting('mediawiker_pagelist', {})
        self.my_pages = mediawiker_pagelist[site_name_active] if site_name_active in mediawiker_pagelist else []
        if self.my_pages:
            self.my_pages.reverse()
            #error 'Quick panel unavailable' fix with timeout..
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.my_pages, self.on_done), 1)
        else:
            sublime.status_message('List of pages for wiki "%s" is empty.' % (site_name_active))

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            title = self.my_pages[index]
            try:
                self.window.run_command("mediawiker_page", {"title": title, "action": "mediawiker_show_page"})
            except ValueError as e:
                sublime.message_dialog(e)


class MediawikerValidateConnectionParamsCommand(sublime_plugin.WindowCommand):
    site = None
    password = ''
    title = ''
    action = ''

    def run(self, title, action):
        self.action = action  # TODO: check for better variant
        self.title = title
        site = mw_get_setting('mediawiki_site_active')
        site_list = mw_get_setting('mediawiki_site')
        self.password = site_list[site]["password"]
        if site_list[site]["username"]:
            #auth required if username exists in settings
            if not self.password:
                #need to ask for password
                self.window.show_input_panel('Password:', '', self.on_done, None, None)
            else:
                self.call_page()
        else:
            #auth is not required
            self.call_page()

    def on_done(self, password):
        self.password = password
        self.call_page()

    def call_page(self):
        #TODO: if havent opened views get error.. 'NoneType' object has no attribute 'run_command'.. need to fix..
        self.window.active_view().run_command(self.action, {"title": self.title, "password": self.password})


class MediawikerShowPageCommand(sublime_plugin.TextCommand):

    def run(self, edit, title, password):
        is_writable = False
        sitecon = mw_get_connect(password)
        is_writable, text = mw_get_page_text(sitecon, title)
        if is_writable and not text:
            sublime.status_message('Wiki page %s is not exists. You can create new..' % (title))
            text = '<New wiki page: Remove this with text of the new page>'
        if is_writable:
            self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.set_syntax_file('Packages/Mediawiker/Mediawiki.tmLanguage')
            self.view.set_name(title)
            self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': text})
            sublime.status_message('Page %s was opened successfully.' % (title))


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit, title, password):
        sitecon = mw_get_connect(password)
        self.title = mw_get_title()
        if self.title:
            self.page = sitecon.Pages[self.title]
            if self.page.can('edit'):
                self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
                summary_message = 'Changes summary (%s):' % mw_get_setting('mediawiki_site_active')
                self.view.window().show_input_panel(summary_message, '', self.on_done, None, None)
            else:
                sublime.status_message('You have not rights to edit this page')
        else:
            sublime.status_message('Can\'t publish page with empty title')
            return

    def on_done(self, summary):
        try:
            summary = '%s%s' % (summary, mw_get_setting('mediawiker_summary_postfix', ' (by SublimeText.Mediawiker)'))
            mark_as_minor = mw_get_setting('mediawiker_mark_as_minor')
            if self.page.can('edit'):
                #invert minor settings command '!'
                if summary[0] == '!':
                    mark_as_minor = not mark_as_minor
                    summary = summary[1:]
                self.page.save(self.current_text, summary=summary.strip(), minor=mark_as_minor)
            else:
                sublime.status_message('You have not rights to edit this page')
        except mwclient.EditError as e:
            sublime.status_message('Can\'t publish page %s (%s)' % (self.title, e))
        sublime.status_message('Wiki page %s was successfully published to wiki.' % (self.title))
        #save my pages
        mw_save_mypages(self.title)


class MediawikerShowTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []

    def run(self, edit):
        self.items = []
        self.regions = []
        tab = ' ' * 4
        pattern = r'^(={1,5})\s?(.*?)\s?={1,5}'
        self.regions = self.view.find_all(pattern)
        for r in self.regions:
            item = sub(pattern, r'\1\2', self.view.substr(r)).replace('=', tab)
            self.items.append(item)
        sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_done), 1)

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            self.view.show(self.regions[index])
            self.view.sel().clear()
            self.view.sel().add(self.regions[index])


class MediawikerEnumerateTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []

    def run(self, edit):
        self.items = []
        self.regions = []
        pattern = '^={1,5}(.*)?={1,5}'
        self.regions = self.view.find_all(pattern)
        header_level_number = [0, 0, 0, 0, 0]
        len_delta = 0
        for r in self.regions:
            if len_delta:
                #prev. header text was changed, move region to new position
                r_new = sublime.Region(r.a + len_delta, r.b + len_delta)
            else:
                r_new = r
            region_len = r_new.b - r_new.a
            header_text = self.view.substr(r_new)
            level = mw_get_hlevel(header_text, "=")
            current_number_str = ''
            i = 1
            #generate number value, start from 1
            while i <= level:
                position_index = i - 1
                header_number = header_level_number[position_index]
                if i == level:
                    #incr. number
                    header_number += 1
                    #save current number
                    header_level_number[position_index] = header_number
                    #reset sub-levels numbers
                    header_level_number[i:] = [0] * len(header_level_number[i:])
                if header_number:
                    current_number_str = "%s.%s" % (current_number_str, header_number) if current_number_str else '%s' % (header_number)
                #incr. level
                i += 1

            #get title only
            header_text_clear = header_text.strip(' =\t')
            header_text_clear = sub(r'^(\d\.)+\s+(.*)', r'\2', header_text_clear)
            header_tag = '=' * level
            header_text_numbered = '%s %s. %s %s' % (header_tag, current_number_str, header_text_clear, header_tag)
            len_delta += len(header_text_numbered) - region_len
            self.view.replace(edit, r_new, header_text_numbered)


class MediawikerSetActiveSiteCommand(sublime_plugin.WindowCommand):
    site_keys = []
    site_on = '>'
    site_off = ' ' * 3

    def run(self):
        site_active = mw_get_setting('mediawiki_site_active')
        sites = mw_get_setting('mediawiki_site')
        self.site_keys = list(sites.keys())
        for key in self.site_keys:
            checked = self.site_on if key == site_active else self.site_off
            self.site_keys[self.site_keys.index(key)] = '%s %s' % (checked, key)
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.site_keys, self.on_done), 1)

    def on_done(self, index):
        # not escaped and not active
        if index >= 0 and self.site_on != self.site_keys[index][:len(self.site_on)]:
            mw_set_setting("mediawiki_site_active", self.site_keys[index].strip())


class MediawikerOpenPageInBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
        url = mw_get_page_url()
        if url:
            webbrowser.open(url)
        else:
            sublime.status_message('Can\'t open page with empty title')
            return


class MediawikerAddCategoryCommand(sublime_plugin.TextCommand):
    categories_list = None
    password = ''
    title = ''

    def run(self, edit, title, password):
        sitecon = mw_get_connect(self.password)
        category_root = mw_get_category(mw_get_setting('mediawiker_category_root'))[1]
        category = sitecon.Categories[category_root]
        self.categories_list_names = []
        self.categories_list_values = []

        for page in category:
            if page.namespace == CATEGORY_NAMESPACE:
                self.categories_list_values.append(page.name)
                self.categories_list_names.append(page.name[page.name.find(':') + 1:])
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.categories_list_names, self.on_done), 1)

    def on_done(self, idx):
        # the dialog was cancelled
        if idx is -1:
            return
        index_of_textend = self.view.size()
        self.view.run_command('mediawiker_insert_text', {'position': index_of_textend, 'text': '[[%s]]' % self.categories_list_values[idx]})


class MediawikerCsvTableCommand(sublime_plugin.TextCommand):
    ''' selected text, csv data to wiki table '''
    #TODO: rewrite as simple to wiki command
    def run(self, edit):
        delimiter = mw_get_setting('mediawiker_csvtable_delimiter', '|')
        table_header = '{|'
        table_footer = '|}'
        table_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_properties', {}).items()])
        cell_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_cell_properties', {}).items()])
        if cell_properties:
            cell_properties = ' %s | ' % cell_properties

        selected_regions = self.view.sel()
        for reg in selected_regions:
            table_data_dic_tmp = []
            table_data = ''
            for line in self.view.substr(reg).split('\n'):
                if delimiter in line:
                    row = line.split(delimiter)
                    table_data_dic_tmp.append(row)

            #verify and fix columns count in rows
            cols_cnt = len(max(table_data_dic_tmp, key=len))
            for row in table_data_dic_tmp:
                len_diff = cols_cnt - len(row)
                while len_diff:
                    row.append('')
                    len_diff -= 1

            for row in table_data_dic_tmp:
                if table_data:
                    table_data += '\n|-\n'
                    column_separator = '||'
                else:
                    table_data += '|-\n'
                    column_separator = '!!'
                for col in row:
                    col_sep = column_separator if row.index(col) else column_separator[0]
                    table_data += '%s%s%s ' % (col_sep, cell_properties, col)

            self.view.replace(edit, reg, '%s %s\n%s\n%s' % (table_header, table_properties, table_data, table_footer))


class MediawikerEditPanelCommand(sublime_plugin.WindowCommand):
    options = []

    def run(self):
        snippet_tag = u'\u24C8'
        self.options = mw_get_setting('mediawiker_panel', {})
        if self.options:
            office_panel_list = ['\t%s' % val['caption'] if val['type'] != 'snippet' else '\t%s %s' % (snippet_tag, val['caption']) for val in self.options]
            self.window.show_quick_panel(office_panel_list, self.on_done)

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            try:
                action_type = self.options[index]['type']
                action_value = self.options[index]['value']
                if action_type == 'snippet':
                    #run snippet
                    self.window.active_view().run_command("insert_snippet", {"name": action_value})
                elif action_type == 'window_command':
                    #run command
                    self.window.run_command(action_value)
                elif action_type == 'text_command':
                    #run command
                    self.window.active_view().run_command(action_value)
            except ValueError as e:
                sublime.status_message(e)


class MediawikerTableWikiToSimpleCommand(sublime_plugin.TextCommand):
    ''' convert selected (or under cursor) wiki table to Simple table (TableEdit plugin) '''

    #TODO: wiki table properties will be lost now...
    def run(self, edit):
        selection = self.view.sel()
        table_region = None

        if not self.view.substr(selection[0]):
            table_region = self.gettable()
        else:
            for reg in selection:
                table_region = reg
                break  # only first region will be proceed..

        if table_region:
            text = self.tblfixer(self.view.substr(table_region))
            table_data = self.table_parser(text)
            self.view.replace(edit, table_region, self.drawtable(table_data))
            #Turn on TableEditor
            try:
                self.view.run_command('table_editor_enable_for_current_view', {'prop': 'enable_table_editor'})
            except Exception as e:
                sublime.status_message('Need to correct install plugin TableEditor: %s' % e)

    def table_parser(self, text):
        is_table = False
        is_row = False
        TBL_START = '{|'
        TBL_STOP = '|}'
        TBL_ROW_START = '|-'
        CELL_FIRST_DELIM = '|'
        CELL_DELIM = '||'
        #CELL_HEAD_FIRST_DELIM = '!'
        CELL_HEAD_DELIM = '!!'
        CELL_FIRST_DELIM = '|'
        is_table_has_header = False
        table_data = []

        for line in text.split('\n'):
            is_header = False
            line = line.replace('\n', '')
            if line[:2] == TBL_START:
                is_table = True
            if line[:2] == TBL_STOP:
                is_table = False
            if line[:2] == TBL_ROW_START:
                is_row = True
            if is_table and is_row and line[:2] != TBL_ROW_START:
                row_data = []
                line = self.delim_fixer(line)  # temp replace char | in cell properties to """"
                if CELL_DELIM in line:
                    cells = line.split(CELL_DELIM)
                elif CELL_HEAD_DELIM in line:
                    cells = line.split(CELL_HEAD_DELIM)
                    is_table_has_header = True
                for cell in cells:
                    if CELL_FIRST_DELIM in cell:
                        #cell properties exists
                        try:
                            props_data, cell_data = [val.strip() for val in cell.split(CELL_FIRST_DELIM)]
                            props_data = props_data.replace('""""', CELL_FIRST_DELIM)
                        except Exception as e:
                            print('Incorrect cell! %s' % e)
                    else:
                        props_data, cell_data = '', cell.strip()

                    if is_table_has_header:
                        is_header = True
                        is_table_has_header = False
                    #saving cell properties, but not used now..
                    row_data.append({'properties': props_data, 'cell_data': cell_data, 'is_header': is_header})
                table_data.append(row_data)
        return table_data

    def gettable(self):
        cursor_position = self.view.sel()[0].begin()
        pattern = r'^\{\|(.*\n)*?\|\}'
        regions = self.view.find_all(pattern)
        for reg in regions:
            if reg.a <= cursor_position <= reg.b:
                return reg

    def drawtable(self, table_list):
        '''Draw table as Table editor: Simple table'''
        if not table_list:
            return ''
        text = ''
        need_header = table_list[0][0]['is_header']
        for row in table_list:
            header_line = ''
            if need_header:
                header_line = '|-\n'
                need_header = False  # draw header only first time
            text += '| '
            text += ' | '.join(cell['cell_data'] for cell in row)
            text += ' |\n%s' % header_line
        return text

    def tblfixer(self, text):
        text = sub(r'(.){1}(\|\-)', r'\1\n\2', text)  # |- on the same line as {| - move to next line
        text = sub(r'(\{\|.*\n)([\|\!]\s?[^-])', r'\1|-\n\2', text)  # if |- skipped after {| line, add it
        text = sub(r'\n(\|\s)', r'|| ', text)  # columns to one line
        text = sub(r'(\|\-)(.*?)(\|\|)', r'\1\2\n| ', text)  # |- on it's own line
        return text

    def delim_fixer(self, string_data):
        string_data = string_data[1:]
        tags_start = ['[', '{']
        tags_end = [']', '}']
        CELL_CHAR = '|'
        REPLACE_STR = '""""'
        is_tag = False
        string_out = ''
        for char in string_data:
            if char in tags_start and not is_tag:
                is_tag = True
            if is_tag and char in tags_end:
                is_tag = False
            if is_tag and char == CELL_CHAR:
                string_out += REPLACE_STR
            else:
                string_out += char
        return string_out


class MediawikerTableSimpleToWikiCommand(sublime_plugin.TextCommand):
    ''' convert selected (or under cursor) Simple table (TableEditor plugin) to wiki table '''
    def run(self, edit):
        selection = self.view.sel()
        table_region = None
        if not self.view.substr(selection[0]):
            table_region = self.gettable()
        else:
            for reg in selection:
                table_region = reg
                break  # only first region will be proceed..

        if table_region:
            text = self.view.substr(table_region)
            table_data = self.table_parser(text)
            self.view.replace(edit, table_region, self.drawtable(table_data))

    def table_parser(self, text):
        table_data = []
        TBL_HEADER_STRING = '|-'
        need_header = False
        if text.split('\n')[1][:2] == TBL_HEADER_STRING:
            need_header = True
        for line in text.split('\n'):
            if line:
                row_data = []
                if line[:2] == TBL_HEADER_STRING:
                    continue
                elif line[0] == '|':
                    cells = line[1:-1].split('|')  # without first and last char "|"
                    for cell_data in cells:
                        row_data.append({'properties': '', 'cell_data': cell_data, 'is_header': need_header})
                    if need_header:
                        need_header = False
            if row_data and type(row_data) is list:
                table_data.append(row_data)
        return table_data

    def gettable(self):
        cursor_position = self.view.sel()[0].begin()
        # ^([^\|\n].*)?\n\|(.*\n)*?\|.*\n[^\|] - all tables regexp (simple and wiki)?
        pattern = r'^\|(.*\n)*?\|.*\n[^\|]'
        regions = self.view.find_all(pattern)
        for reg in regions:
            if reg.a <= cursor_position <= reg.b:
                table_region = sublime.Region(reg.a, reg.b - 2)  # minus \n and [^\|]
                return table_region

    def drawtable(self, table_list):
        ''' draw wiki table '''
        TBL_START = '{|'
        TBL_STOP = '|}'
        TBL_ROW_START = '|-'
        CELL_FIRST_DELIM = '|'
        CELL_DELIM = '||'
        CELL_HEAD_FIRST_DELIM = '!'
        CELL_HEAD_DELIM = '!!'

        text_wikitable = ''
        table_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_properties', {}).items()])

        need_header = table_list[0][0]['is_header']
        is_first_line = True
        for row in table_list:
            if need_header or is_first_line:
                text_wikitable += '%s\n%s' % (TBL_ROW_START, CELL_HEAD_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_HEAD_DELIM, row)
                is_first_line = False
                need_header = False
            else:
                text_wikitable += '\n%s\n%s' % (TBL_ROW_START, CELL_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_DELIM, row)

        return '%s %s\n%s\n%s' % (TBL_START, table_properties, text_wikitable, TBL_STOP)

    def getrow(self, delimiter, rowlist=[]):
        cell_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_cell_properties', {}).items()])
        cell_properties = '%s | ' % cell_properties if cell_properties else ''
        try:
            return delimiter.join(' %s%s ' % (cell_properties, cell['cell_data'].strip()) for cell in rowlist)
        except Exception as e:
            print('Error in data: %s' % e)


class MediawikerCategoryListCommand(sublime_plugin.TextCommand):
    password = ''
    pages = {}  # pagenames -> namespaces
    pages_names = []  # pagenames for menu
    category_path = []
    CATEGORY_NEXT_PREFIX_MENU = '> '
    CATEGORY_PREV_PREFIX_MENU = '. . '
    category_prefix = ''  # "Category" namespace name as returned language..

    def run(self, edit, title, password):
        if self.category_path:
            category_root = mw_get_category(self.get_category_current())[1]
        else:
            category_root = mw_get_category(mw_get_setting('mediawiker_category_root'))[1]
        sublime.active_window().show_input_panel('Wiki root category:', category_root, self.show_list, None, None)

    def show_list(self, category_root):
        if not category_root:
            return
        self.pages = {}
        self.pages_names = []

        category_root = mw_get_category(category_root)[1]

        if not self.category_path:
            self.update_category_path('%s:%s' % (self.get_category_prefix(), category_root))

        if len(self.category_path) > 1:
            self.add_page(self.get_category_prev(), CATEGORY_NAMESPACE, False)

        for page in self.get_list_data(category_root):
            if page.namespace == CATEGORY_NAMESPACE and not self.category_prefix:
                    self.category_prefix = mw_get_category(page.name)[0]
            self.add_page(page.name, page.namespace, True)
        if self.pages:
            self.pages_names.sort()
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.pages_names, self.get_page), 1)
        else:
            sublime.message_dialog('Category %s is empty' % category_root)

    def add_page(self, page_name, page_namespace, as_next=True):
        page_name_menu = page_name
        if page_namespace == CATEGORY_NAMESPACE:
            page_name_menu = self.get_category_as_next(page_name) if as_next else self.get_category_as_prev(page_name)
        self.pages[page_name] = page_namespace
        self.pages_names.append(page_name_menu)

    def get_list_data(self, category_root):
        ''' get objects list by category name '''
        sitecon = mw_get_connect(self.password)
        return sitecon.Categories[category_root]

    def get_category_as_next(self, category_string):
        return '%s%s' % (self.CATEGORY_NEXT_PREFIX_MENU, category_string)

    def get_category_as_prev(self, category_string):
        return '%s%s' % (self.CATEGORY_PREV_PREFIX_MENU, category_string)

    def category_strip_special_prefix(self, category_string):
        return category_string.lstrip(self.CATEGORY_NEXT_PREFIX_MENU).lstrip(self.CATEGORY_PREV_PREFIX_MENU)

    def get_category_prev(self):
        ''' return previous category name in format Category:CategoryName'''
        return self.category_path[-2]

    def get_category_current(self):
        ''' return current category name in format Category:CategoryName'''
        return self.category_path[-1]

    def get_category_prefix(self):
        if self.category_prefix:
            return self.category_prefix
        else:
            return 'Category'

    def update_category_path(self, category_string):
        if category_string in self.category_path:
            self.category_path = self.category_path[:-1]
        else:
            self.category_path.append(self.category_strip_special_prefix(category_string))

    def get_page(self, index):
        if index >= 0:
            # escape from quick panel return -1
            page_name = self.category_strip_special_prefix(self.pages_names[index])
            if self.pages[page_name] == CATEGORY_NAMESPACE:
                self.update_category_path(page_name)
                self.show_list(page_name)
            else:
                try:
                    sublime.active_window().run_command("mediawiker_page", {"title": page_name, "action": "mediawiker_show_page"})
                except ValueError as e:
                    sublime.message_dialog(e)


class MediawikerSearchStringListCommand(sublime_plugin.TextCommand):
    password = ''
    title = ''
    search_limit = 20
    pages_names = []
    search_result = None

    def run(self, edit, title, password):
        sublime.active_window().show_input_panel('Wiki search:', '', self.show_results, None, None)

    def show_results(self, search_value=''):
        #TODO: paging?
        self.pages_names = []
        self.search_limit = mw_get_setting('mediawiker_search_results_count')
        if search_value:
            self.search_result = self.do_search(search_value)
        if self.search_result:
            for i in range(self.search_limit):
                try:
                    page_data = self.search_result.next()
                    self.pages_names.append([page_data['title'], page_data['snippet']])
                except:
                    pass
            te = ''
            search_number = 1
            for pa in self.pages_names:
                te += '### %s. %s\n* [%s](%s)\n\n%s\n' % (search_number, pa[0], pa[0], mw_get_page_url(pa[0]), self.antispan(pa[1]))
                search_number += 1

            if te:
                self.view = sublime.active_window().new_file()
                self.view.set_syntax_file('Packages/Markdown/Markdown.tmLanguage')
                self.view.set_name('Wiki search results: %s' % search_value)
                self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': te})
            elif search_value:
                sublime.message_dialog('No results for: %s' % search_value)

    def antispan(self, text):
        span_replace_open = "`"
        span_replace_close = "`"
        #bold and italic tags cut
        text = text.replace("'''", "")
        text = text.replace("''", "")
        #spans to bold
        text = sub(r'<span(.*?)>', span_replace_open, text)
        text = sub(r'<\/span>', span_replace_close, text)
        #divs cut
        text = sub(r'<div(.*?)>', '', text)
        text = sub(r'<\/div>', '', text)
        return text

    def do_search(self, string_value):
        sitecon = mw_get_connect(self.password)
        namespace = mw_get_setting('mediawiker_search_namespaces')
        return sitecon.search(search=string_value, what='text', limit=self.search_limit, namespace=namespace)


class MediawikerAddImageCommand(sublime_plugin.TextCommand):
    password = ''
    image_prefix_min_lenght = 4
    images_names = []

    def run(self, edit, password, title=''):
        self.image_prefix_min_lenght = mw_get_setting('mediawiker_image_prefix_min_length', 4)
        sublime.active_window().show_input_panel('Wiki image prefix (min %s):' % self.image_prefix_min_lenght, '', self.show_list, None, None)

    def show_list(self, image_prefix):
        if len(image_prefix) >= self.image_prefix_min_lenght:
            self.images_names = []
            sitecon = mw_get_connect(self.password)
            images = sitecon.allpages(prefix=image_prefix, namespace=IMAGE_NAMESPACE)  # images list by prefix
            for image in images:
                self.images_names.append(image.page_title)
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.images_names, self.on_done), 1)
        else:
            sublime.message_dialog('Image prefix length must be more than %s. Operation canceled.' % self.image_prefix_min_lenght)

    def on_done(self, idx):
        if idx >= 0:
            index_of_cursor = self.view.sel()[0].begin()
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': '[[Image:%s]]' % self.images_names[idx]})


class MediawikerAddTemplateCommand(sublime_plugin.TextCommand):
    password = ''
    templates_names = []
    sitecon = None

    def run(self, edit, password, title=''):
        self.password = password
        sublime.active_window().show_input_panel('Wiki template prefix:', '', self.show_list, None, None)

    def show_list(self, image_prefix):
        self.templates_names = []
        self.sitecon = mw_get_connect(self.password)
        templates = self.sitecon.allpages(prefix=image_prefix, namespace=TEMPLATE_NAMESPACE)  # images list by prefix
        for template in templates:
            self.templates_names.append(template.page_title)
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.templates_names, self.on_done), 1)

    def get_template_params(self, text):
        params_list = []
        pattern = r'\{{3}.*?\}{3}'
        parameters = findall(pattern, text)
        for param in parameters:
            param = param.strip('{}')
            #default value or not..
            param = param.replace('|', '=') if '|' in param else '%s=' % param
            if param not in params_list:
                params_list.append(param)
        return ''.join(['|%s\n' % param for param in params_list])

    def on_done(self, idx):
        if idx >= 0:
            template = self.sitecon.Pages['Template:%s' % self.templates_names[idx]]
            text = template.edit()
            params_text = self.get_template_params(text)
            index_of_cursor = self.view.sel()[0].begin()
            template_text = '{{%s%s}}' % (self.templates_names[idx], params_text)
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': template_text})


class MediawikerOpenPageCli(sublime_plugin.WindowCommand):

    def run(self):
        proto_prefix = 'mediawiker|'
        views = self.window.views()
        for view in views:
            view_name = view.file_name()
            if view_name is not None:
                #another wiki pages haven't file_name
                view_name = self.proto_replacer(view_name[view_name.find(proto_prefix):])  # strip abs path and make replaces hacks..
                if view_name.startswith(proto_prefix):
                    page_name = mw_pagename_clear(view_name.split('|')[1])
                    if self.window.active_view().is_read_only():
                        if (int(sublime.version()) > 3000):
                            self.window.active_view().set_read_only(False)
                        else:
                            self.window.active_view().set_read_only(0)

                    sublime.set_timeout(lambda: self.window.run_command("mediawiker_page", {"action": "mediawiker_reopen_page", "title": page_name}), 1)

    def proto_replacer(self, page_string):
        return page_string.replace('http!!!\\', 'http://').replace('!!!', ':').replace('\\', '/')
