from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.core.extensions import db
from abilian.services import Service

from .models import Hit, View

__all__ = ['viewtracker']


class ViewTracker(Service):
    name = 'viewtracker'

    @staticmethod
    def record_hit(entity, user):
        # Using user_id here in case user is a threadload proxy
        views = View.query.filter(View.entity == entity,
                                  View.user_id == user.id)
        if views.count():
            view = views.first()
            hit = Hit(view=view)
            db.session.add(hit)

        else:
            view = View(entity=entity, user_id=user.id)
            hit = Hit(view=view)
            db.session.add(view)
            db.session.add(hit)

        # FIXME: not the right place
        db.session.commit()

    @staticmethod
    def get_views(entity=None, entities=None, user=None, users=None):
        assert object or user
        query = View.query
        if entities:
            entities_id = [entity_.id for entity_ in entities]
            query = query.filter(View.entity_id.in_(entities_id))
        elif entity:
            query = query.filter(View.entity_id == entity.id)

        if users:
            users_id = [user_.id for user_ in users]
            query = query.filter(View.user_id.in_(users_id))
        elif user:
            query = query.filter(View.user_id == user.id)

        return query.all()

    @staticmethod
    def get_hits(views=None, view=None):
        query = Hit.query
        if views:
            views_id = [view_.id for view_ in views]
            query = query.filter(Hit.view_id.in_(views_id))\
                .order_by(Hit.viewed_at.asc())
        elif view:
            query = query.filter(Hit.view_id == view.id)\
                .order_by(Hit.viewed_at.asc())

        return query.all()

    # #: get tracks of a specific object and user
    # @staticmethod
    # def get_tracked_object(object, user):
    #     view_objects = View.query \
    #         .filter(View.object == object, View.user == user) \
    #         .first()
    #     return view_objects
    #
    # # get all viewers of a specific object
    # @staticmethod
    # def get_viewers(object):
    #     view_objects = View.query \
    #         .filter(View.object == object) \
    #         .all()
    #     return view_objects
    #
    # # get all ViewView objects from a specific user
    # @staticmethod
    # def get_viewed_objects(user_id):
    #     view_objects = View.query \
    #         .filter(View.user_id == user_id) \
    #         .all()
    #     return view_objects

    # Instanciate the service


viewtracker = ViewTracker()
