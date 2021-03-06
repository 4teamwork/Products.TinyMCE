from zope.interface import implements
try:
    import simplejson as json
    json   # pyflakes
except ImportError:
    import json

from Products.TinyMCE.adapters.interfaces.JSONSearch import IJSONSearch


class JSONSearch(object):
    """Returns a list of search results in JSON"""
    implements(IJSONSearch)

    def __init__(self, context):
        """Constructor"""
        self.context = context

    def getSearchResults(self, filter_portal_types, searchtext):
        """Returns the actual search result"""

        if '*' not in searchtext:
            searchtext += '*'

        catalog_results = []
        results = {
            'parent_url': '',
            'path': [],
        }
        query = {
            'portal_type': filter_portal_types,
            'sort_on': 'sortable_title',
            'path': '/'.join(self.context.getPhysicalPath()),
            'SearchableText': searchtext,
        }
        if searchtext:
            plone_layout = self.context.restrictedTraverse('@@plone_layout',
                                                           None)
            if plone_layout is None:
                # Plone 3
                plone_view = self.context.restrictedTraverse('@@plone')
                getIcon = lambda brain: plone_view.getIcon(brain).html_tag()
            else:
                # Plone >= 4
                getIcon = lambda brain: plone_layout.getIcon(brain)()

            brains = self.context.portal_catalog.searchResults(**query)

            for brain in brains:
                if not brain:
                    # With solr, brain is sometimes None
                    # https://github.com/4teamwork/izug.organisation/issues/664
                    continue

                catalog_results.append({
                    'id': brain.getId,
                    'uid': brain.UID,
                    'url': brain.getURL(),
                    'portal_type': brain.portal_type,
                    'title': brain.Title == "" and brain.id or brain.Title,
                    'icon': getIcon(brain),
                    'description': brain.Description,
                    'is_folderish': brain.is_folderish,
                    })

        # add catalog_results
        results['items'] = catalog_results

        # never allow upload from search results page
        results['upload_allowed'] = False

        # return results in JSON format
        self.context.REQUEST.response.setHeader("Content-type",
                                                "application/json")
        return json.dumps(results)
