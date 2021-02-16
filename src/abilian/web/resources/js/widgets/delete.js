/**
 Allow to setup a delete button for urls managed by abilian.web.views.object.ObjectDelete.
 */
require(["AbilianWidget", "jquery", "bootbox"], (Abilian, $, bootbox) => {
  "use strict";

  const defaults = {
    title: "La suppression est irréversible",
    message: "Do you really want to delete this entity ?",
    label: "Delete",
    cancelLabel: "Cancel",
  };

  function ConfirmDialog(elt, options) {
    "use strict";

    const self = this;
    this.elt = elt;
    this.options = $.extend({}, defaults, options);
    this.url = elt.attr("href");
    elt.on("click", (e) => {
      e.preventDefault();
      self.openModal();
    });
  }

  ConfirmDialog.prototype.openModal = function () {
    const self = this;
    const title = `<strong class="text-danger"><i class="glyphicon glyphicon-warning-sign"></i> ${this.options.title}</strong>`;

    bootbox.dialog({
      title: title,
      message: `<p class="lead">${this.options.message}</p>`,
      closeButton: true,
      buttons: {
        confirm: {
          label: this.options.label,
          className: "btn-danger", // or btn-primary, or btn-danger, or nothing at all
          callback() {
            self.onConfirm();
          },
        },
        cancel: {
          label: this.options.cancelLabel,
          className: "", // or btn-primary, or btn-danger, or nothing at all
        },
      },
      keyboard: true,
    });
  };

  ConfirmDialog.prototype.onConfirm = function () {
    // Hack to provoke a POST instead of a GET.
    const form = document.createElement("form");
    form.setAttribute("method", "POST");
    form.setAttribute("action", this.url);
    form.setAttribute("enctype", "multipart/form-data");

    // csrf
    const input1 = document.createElement("input");
    input1.setAttribute("type", "hidden");
    input1.setAttribute("name", Abilian.csrf_fieldname);
    input1.setAttribute("value", Abilian.csrf_token);
    form.appendChild(input1);

    // action value
    const input2 = document.createElement("input");
    input2.setAttribute("type", "hidden");
    input2.setAttribute("name", "__action");
    input2.setAttribute("value", "delete");
    form.appendChild(input2);

    document.body.appendChild(form);
    form.submit();
  };

  function setupDeleteConfirm(params) {
    return new ConfirmDialog($(this), params);
  }

  Abilian.registerWidgetCreator("deleteConfirm", setupDeleteConfirm);
});
