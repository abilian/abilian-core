# Draft API for various services.

These are works in progress which need to be reviewed before being implemented.


## Current and planned services

### Core services

SearchService.

AuditService.

TransformationService.

-> These services are already implemented but may benefit from some refactoring.


### Currently on customer projet, needs to be made more generic and moved here

SecurityService.


### implementation not started yet

TagService: allows tagging of resources.

LikeService: allows liking (and possibly unliking) of resources.

RatingService: allows user rating (typically, 0 to 5 stars) on resources
(entities or activities).

CommentService: allows user comments on resources (entities or activities).

AccessLogService: logs access to resources (may be turned on/off on a per
container basis).


## Other considerations

We will probably want to expose these services (and more) as RESTful
web services.

------------------------------------------------------------------------------

## Questions

- Do we explicit pass a user when needed, or do we rely on the current_user
  from the thread local ?
