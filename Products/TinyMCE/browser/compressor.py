"""
Based on "TinyMCE Compressor PHP" from MoxieCode.

http://tinymce.moxiecode.com/

Copyright (c) 2008 Jason Davies
Licensed under the terms of the MIT License (see LICENSE.txt)
"""

from datetime import datetime

try:
    import simplejson as json
    json  # pyflakes
except ImportError:
    import json

import zope.component
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.ResourceRegistries.tools.packer import JavascriptPacker

from Products.TinyMCE.interfaces.utility import ITinyMCE


BUTTON_WIDTHS = {'style': 150, 'forecolor': 32, 'backcolor': 32, 'tablecontrols': 285}


class TinyMCECompressorView(BrowserView):
    tiny_mce_gzip = ViewPageTemplateFile('tiny_mce_gzip.js')

    # TODO: cache
    def __call__(self):
        plugins = self.request.get("plugins", "").split(',')
        languages = self.request.get("languages", "").split(',')
        themes = self.request.get("themes", "").split(',')
        isJS = self.request.get("js", "") == "true"
        suffix = self.request.get("suffix", "") == "_src" and "_src" or ""
        response = self.request.response
        response.headers["Content-Type"] = "text/javascript"

        plone_portal_state = zope.component.getMultiAdapter(
                (self.context, self.request), name="plone_portal_state")
        portal_url = plone_portal_state.portal_url()
        base_url = '/'.join([self.context.absolute_url(), self.__name__])

        if not isJS:
            utility = zope.component.queryUtility(ITinyMCE)
            config = utility.getConfiguration(
                context=self.context,
                request=self.request,
                as_json=False
            )

            tiny_mce_gzip = self.tiny_mce_gzip(base_url=base_url,
                                      config=config,
                                      jsondumps=json.dumps,
                                      portal_url=portal_url,
                                      plugins=TinyMCECompressorView.getplugins(config),
                                      styles=TinyMCECompressorView.getstyles(config),
                                      labels=TinyMCECompressorView.getlabels(config),
                                      valid_elements=TinyMCECompressorView.getvalidelements(config),
                                      link_shortcuts_html=json.dumps(config['link_shortcuts_html']),
                                      image_shortcuts_html=json.dumps(config['image_shortcuts_html']),
                                      thumbnail_size=json.dumps(config['thumbnail_size']),
                                      toolbars=TinyMCECompressorView.gettoolbars(config))
            return JavascriptPacker('full').pack(tiny_mce_gzip)

        now = datetime.utcnow()
        response['Date'] = now.strftime('%a, %d %b %Y %H:%M:%S GMT')

        traverse = lambda name: str(self.context.restrictedTraverse(name, ''))

        # Add core, with baseURL added
        content = [
            traverse("tiny_mce%s.js" % suffix).replace(
                "tinymce._init();",
                "tinymce.baseURL='%s';tinymce._init();" % base_url)
        ]

        # Add core languages
        # TODO: we have our own translations
        for lang in languages:
            content.append(traverse("langs/%s.js" % lang))

        # Add themes
        for theme in themes:
            content.append(traverse("themes/%s/editor_template%s.js" % (theme, suffix)))

            for lang in languages:
                content.append(traverse("themes/%s/langs/%s.js" % (theme, lang)))

        # Add plugins
        for plugin in plugins:
            content.append(traverse("plugins/%s/editor_plugin%s.js" % (plugin, suffix)))

            for lang in languages:
                content.append(traverse("plugins/%s/langs/%s.js" % (plugin, lang)))

        # TODO: add aditional javascripts in plugins

        return ''.join(content)

    # make this easier to override by childs until we provide this via the control panel
    default_plugins = ("pagebreak,table,save,advhr,emotions,insertdatetime,"
                       "preview,media,searchreplace,print,paste,"
                       "directionality,fullscreen,noneditable,visualchars,"
                       "nonbreaking,xhtmlxtras,inlinepopups,plonestyle,"
                       "tabfocus,definitionlist,ploneinlinestyles")

    @staticmethod
    def getplugins(config):
        plugins = TinyMCECompressorView.default_plugins
        sp = config['libraries_spellchecker_choice']
        sp = sp != "browser" and sp or ""
        if sp:
            plugins += ',' + sp

        for plugin in config['customplugins']:
            if '|' not in plugin:
                plugins += ',' + plugin
            else:
                plugins += ',' + plugin.split('|')[0]

        if config['contextmenu']:
            plugins += ',contextmenu'

        if config['autoresize']:
            plugins += ',autoresize'
        return plugins

    @staticmethod
    def getstyles(config):
        h = {'Text': [], 'Selection': [], 'Tables': [], 'Lists': [], 'Print': []}
        styletype = ""

        # Push title
        h['Text'].append('{ title: "Text", tag: "", className: "-", type: "Text" }')
        h['Selection'].append('{ title: "Selection", tag: "", className: "-", type: "Selection" }')
        h['Tables'].append('{ title: "Tables", tag: "table", className: "-", type: "Tables" }')
        h['Lists'].append('{ title: "Lists", tag: "ul", className: "-", type: "Lists" }')
        h['Lists'].append('{ title: "Lists", tag: "ol", className: "-", type: "Lists" }')
        h['Lists'].append('{ title: "Lists", tag: "dl", className: "-", type: "Lists" }')
        h['Print'].append('{ title: "Print", tag: "", className: "-", type: "Print" }')

        # Add defaults
        h['Text'].append('{ title: "' + config['labels']['label_paragraph'] + '", tag: "p", className: "", type: "Text" }')
        h['Selection'].append('{ title: "' + config['labels']['label_styles'] + '", tag: "", className: "", type: "Selection" }')
        h['Tables'].append('{ title: "' + config['labels']['label_plain_cell'] + '", tag: "td", className: "", type: "Tables" }')
        h['Lists'].append('{ title: "' + config['labels']['label_lists'] + '", tag: "dl", className: "", type: "Lists" }')

        for i in config['styles']:
            e = i.split('|')
            while len(e) <= 2:
                e.append("")
            if e[1].lower() in ('del', 'ins', 'span'):
                    styletype = "Selection"
            elif e[1].lower() in ('table', 'tr', 'td', 'th'):
                    styletype = "Tables"
            elif e[1].lower() in ('ul', 'ol', 'li', 'dt', 'dd', 'dl'):
                    styletype = "Lists"
            else:
                    styletype = "Text"

            if e[2] == "pageBreak":
                    styletype = "Print"
            h[styletype].append('{ title: "' + e[0] + '", tag: "' + e[1] + '", className: "' + e[2] + '", type: "' + styletype + '" }')

            # Add items to list
            a = []
            if len(h['Text']) > 1:
                a.extend(h['Text'])
            if len(h['Selection']) > 1:
                a.extend(h['Selection'])
            if len(h['Tables']) > 1:
                a.extend(h['Tables'])
            if len(h['Lists']) > 1:
                a.extend(h['Lists'])
            if len(h['Print']) > 1:
                a.extend(h['Print'])

        return '[' + ','.join(a) + ']'

    @staticmethod
    def getlabels(config):
        return str(dict([(key, val.encode('utf-8')) for key, val in config['labels'].iteritems()]))

    @staticmethod
    def gettoolbars(config):
        """Calculate number of toolbar rows from length of buttons"""
        t = [[], [], [], []]
        cur_toolbar = 0
        cur_x = 0

        for i in config['buttons']:
            button_width = BUTTON_WIDTHS.get(i, 23)
            if cur_x + button_width > int(config['toolbar_width']):
                cur_x = button_width
                cur_toolbar += 1
            else:
                cur_x += button_width
            if cur_toolbar <= 3:
                t[cur_toolbar].append(i)

        return [','.join(toolbar) for toolbar in t]

    @staticmethod
    def getvalidelements(config):
            a = []
            valid_elements = config['valid_elements']

            for valid_element in valid_elements:
                s = valid_element
                if (valid_elements[valid_element]):
                    s += '[' + '|'.join(valid_elements[valid_element]) + ']'
                a.append(s)
            return ','.join(a)
