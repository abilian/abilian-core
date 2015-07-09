/* jshint unused: false */
/**
 Allow to setup a delete button for urls managed by abilian.web.views.object.ObjectDelete.
*/
(function(factory) {
    'use strict';
    require(['AbilianWidget', 'jquery', 'bootbox'], factory);
}
 (function(Abilian, $, bootbox) {
     'use strict';

     var defaults = {
         title: 'La suppression est irréversible',
         message: 'Do you really want to delete this entity ?',
         label: 'Delete',
         cancelLabel: 'Cancel'
     };

     function ConfirmDialog(elt, options) {
         var self = this;
         this.elt = elt;
         this.options = $.extend({}, defaults, options);
         this.url = elt.attr('href');
         elt.on('click',
                function(e) {
                    e.preventDefault();
                    self.openModal(); }
               );
     }

     ConfirmDialog.prototype.openModal = function () {
         var self = this,
             title = '<strong class="text-danger">' +
                 '<i class="glyphicon glyphicon-warning-sign"></i> ' +
                 this.options.title +
                 '</strong>';

         bootbox.dialog({
             title: title,
             message: '<p class="lead">' + this.options.message + '</p>',
             closeButton: true,
             buttons: {
                 confirm: {
                     'label' : this.options.label,
                     'className' : 'btn-danger',   // or btn-primary, or btn-danger, or nothing at all
                     'callback': function() { self.onConfirm(); }
                 },
                 cancel: {
                     'label' : this.options.cancelLabel,
                     'className' : ''  // or btn-primary, or btn-danger, or nothing at all
                 }
             },
             'keyboard': true
         });
     };

     ConfirmDialog.prototype.onConfirm = function() {
         // Hack to provoke a POST instead of a GET.
         var form = document.createElement("form");
         form.setAttribute("method", "POST");
         form.setAttribute("action", this.url);
         form.setAttribute('enctype', 'multipart/form-data');
         // csrf
         var input = document.createElement('input');
         input.setAttribute('type', 'hidden');
         input.setAttribute('name', Abilian.csrf_fieldname);
         input.setAttribute('value', Abilian.csrf_token);
         form.appendChild(input);
         // action value
         input = document.createElement('input');
         input.setAttribute('type', 'hidden');
         input.setAttribute('name', '__action');
         input.setAttribute('value', 'delete');
         form.appendChild(input);

         document.body.appendChild(form);
         form.submit();
     };

     function setupDeleteConfirm(params) {
         new ConfirmDialog(this, params);
     }

     Abilian.registerWidgetCreator('deleteConfirm', setupDeleteConfirm);
     return setupDeleteConfirm;
}));
