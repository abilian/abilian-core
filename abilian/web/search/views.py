# coding=utf-8
"""
"""
from __future__ import absolute_import

from functools import partial
from collections import OrderedDict

import whoosh.sorting
from flask import Blueprint, request, g, render_template, current_app, url_for

from abilian.i18n import _
from abilian.web import nav

#
# Some hardcoded settings (for now)
#
PAGE_SIZE = 20
MAX_LIVE_RESULTS_PER_CLASS = 5

search = Blueprint('search', __name__, url_prefix="/search",
                   template_folder='templates')
route = search.route

def friendly_fqcn(fqcn):
  return fqcn.rsplit(u'.', 1)[-1]

@search.url_value_preprocessor
def init_search(endpoint, values):
  q = request.args.get("q")
  try:
    page = max(int(request.args.get('page', 1), 1))
  except:
    page = 1

  g.breadcrumb.append(
    nav.BreadcrumbItem(
      label=u'"{}"'.format(q),
      icon="search",
      url=nav.Endpoint('search.search_main', q=q)
      )
    )

  page_kw = OrderedDict(q=q)
  object_types = request.args.getlist('object_type')

  if object_types:
    page_kw['object_type'] = object_types
    g.breadcrumb.append(
      nav.BreadcrumbItem(
        label=u' | '.join(friendly_fqcn(name) for name in object_types),
        url=nav.Endpoint('search.search_main', **page_kw)
      )
    )

  if page > 1:
    g.breadcrumb.append(nav.BreadcrumbItem(
      label=unicode(page),
      url=nav.Endpoint('search.search_main', page=page, **page_kw)
      ))

  values['q'] = q
  values['page'] = page

@search.context_processor
def install_hit_to_url():
  def url_for_hit(hit):
    object_type = hit['object_type']
    object_id = int(hit['id'])
    try:
      return current_app.default_view.url_for(hit, object_type, object_id)
    except KeyError:
      return u'#'

  return dict(url_for_hit=url_for_hit)

@route('')
def search_main(q=u'', page=1):
  svc = current_app.services['indexing']
  search_kwargs = {'limit': page * PAGE_SIZE,}
  page_url_kw = OrderedDict(q=q)

  filtered_by_type = request.args.getlist('object_type')
  if filtered_by_type:
    #FIXME: sanitize input
    types = [whoosh.query.Term('object_type', t) for t in filtered_by_type]
    search_kwargs['filter'] = whoosh.query.Or(types)
    page_url_kw['object_type'] = filtered_by_type
  else:
    search_kwargs['groupedby'] = whoosh.sorting.FieldFacet("object_type",
                                                           maptype=whoosh.sorting.Count)

  results = svc.search(q, **search_kwargs)
  page_url = partial(url_for, '.search_main', **page_url_kw)

  # get facets groups
  by_object_type = []
  try:
    facet_group = results.groups('object_type')
  except KeyError:
    pass
  else:
    for typename, count in facet_group.items():
      classname = friendly_fqcn(typename)
      link = page_url(object_type=typename)
      by_object_type.append((classname, count, link))

  # paginate results
  results = whoosh.searching.ResultsPage(results, page, PAGE_SIZE)

  page = results.pagenum
  prev_page = page_url(page=page-1) if page > 0 else None
  next_page = page_url(page=+1) if page < results.pagecount else None

  return render_template('search/search.html',
                         q=q,
                         results=results,
                         filtered_by_type=filtered_by_type,
                         by_object_type=by_object_type,
                         prev_page=prev_page,
                         next_page=next_page,
                         friendly_fqcn=friendly_fqcn,)
