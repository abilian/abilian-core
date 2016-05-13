# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import datetime

from flask import request
from flask_login import current_user
from flask_sqlalchemy import BaseQuery
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relation

from abilian.core.extensions import db
from abilian.core.models.subjects import User

_MARK = object()


class LoginSessionQuery(BaseQuery):

    def get_active_for(self, user, user_agent=_MARK, ip_address=_MARK):
        """
        Returns last known session for user

        :param user: user session
        :type user: `abilian.core.models.subjects.User`

        :param user_agent: *exact* user agent string to lookup, or `None` to have
        user_agent extracted from request object. If not provided at all, no
        filtering on user_agent.
        :type user_agent: string or None, or absent

        :param ip_address: client IP, or `None` to have ip_address extracted from
        request object (requires header 'X-Forwarded-For'). If not provided at
        all, no filtering on ip_address.
        :type ip_address: string or None, or absent

        :rtype: `LoginSession` or `None` if no session is found.
        """
        conditions = [LoginSession.user == user]

        if user_agent is not _MARK:
            if user_agent is None:
                user_agent = request.environ.get('HTTP_USER_AGENT', '')
            conditions.append(LoginSession.user_agent == user_agent)

        if ip_address is not _MARK:
            if ip_address is None:
                ip_address = request.headers.getlist("X-Forwarded-For")
                ip_address = ip_address[
                    0] if ip_address else request.remote_addr
            conditions.append(LoginSession.ip_address == ip_address)

        session = LoginSession.query \
            .filter(*conditions) \
            .order_by(LoginSession.id.desc()) \
            .first()
        return session


class LoginSession(db.Model):

    __tablename__ = 'login_session'
    query_class = LoginSessionQuery

    id = Column(Integer, primary_key=True, autoincrement=True)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime)

    user_id = Column(ForeignKey(User.id), nullable=False)
    user = relation(User)

    #: IP addres, should work with both IPv4 and IPv6.
    # FIXME: define a custom type to use postgres inet when on postgres
    # http://www.postgresql.org/docs/9.1/static/datatype-net-types.html
    ip_address = Column(String(39), default="", nullable=False)

    #: Limited (somewhat artbitrarily) to 512 characters.
    user_agent = Column(String(512), default="", nullable=False)

    @staticmethod
    def new():
        user_agent = request.environ.get('HTTP_USER_AGENT', '')
        if not request.headers.getlist("X-Forwarded-For"):
            ip_address = request.remote_addr
        else:
            ip_address = request.headers.getlist("X-Forwarded-For")[0]
        session = LoginSession(user=current_user,
                               user_agent=user_agent,
                               ip_address=ip_address)
        return session
