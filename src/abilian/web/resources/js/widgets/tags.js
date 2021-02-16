require(["AbilianWidget", "jquery"], (Abilian, $) => {
  "use strict";

  function initTagsSelect(params) {
    const opts = {
      multiple: true,
      separator: ";",
    };
    $.extend(opts, params);

    // as of Select2 3.5, we cannot use a <select> and
    // createSearchChoices. We must convert it to a hidden input
    const values = (this.val() || []).join(opts.separator);
    const choices = $.map(this.get(0).options, (option) => option.value);
    const input = $('<input type="hidden" />')
      .attr({ name: this.attr("name") })
      .val(values);

    opts.tags = choices;
    input.insertBefore(this);
    this.remove();
    return Abilian.getWidgetCreator("select2").call(input, opts);
  }

  Abilian.registerWidgetCreator("tags-select", initTagsSelect);
});
