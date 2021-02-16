require(["AbilianWidget", "jquery"], (Abilian, $) => {
  "use strict";
  // multiple row widget
  function DynamicRowWidget(table, options) {
    console.log(this);

    const self = this;
    self.table = table;
    self.prefix = table.data("prefix");
    self.tbody = table.children("tbody");
    self.options = options;
    if (self.options == null) {
      self.options = "top";
    }
    self.currentIndex = table.find("> tbody > tr").length;
    self.table.addClass("dynamic-row-widget");
    self.addButton = $(
      '<th><span class="glyphicon glyphicon-plus"></span></th>'
    );
    self.addButton.css({ width: "1em" });
    self.addButton.click((e) => {
      self.addRow();
      e.preventDefault();
    });

    self.minusButton = $(
      '<td><span class="glyphicon glyphicon-remove"></span></td>'
    );
    self.minusButton.click(function (e) {
      $(this).closest("tr").remove();
      e.preventDefault();
    });
    if (self.options.indexOf("top") > -1) {
      table.find("> thead > tr").append(self.addButton);
    }
    if (self.options.indexOf("bottom") > -1) {
      const bottom_addButton = self.addButton.clone();
      bottom_addButton.click((e) => {
        self.addRow();
        e.preventDefault();
      });
      table.find("> tfoot > tr").append(bottom_addButton);
    }
    table.find("> tbody > tr").append(self.minusButton);

    self.templateRow = table.find("tbody > tr:first").clone(true, true);
    /* remove value except for specific controls that have constant (and
     * required) value
     */
    self.templateRow
      .find(
        "input" +
          '[type!="checkbox"]' +
          '[type!="radio"]' +
          '[data-short-name!="csrf_token"]'
      )
      .attr("value", "");
    self.templateRow.find("textarea").text("");
  }

  DynamicRowWidget.prototype = {
    addRow() {
      const self = this;
      const newRow = self.templateRow.clone(true, true);

      newRow.find("input").each(function () {
        const item = $(this);
        const shortName = item.data("shortName");
        let name = `${self.prefix}-${self.currentIndex}`;
        if (shortName) {
          name = `${name}-${shortName}`;
        }
        item.attr("name", name);
        item.attr("id", name);
      });
      newRow.find("select").each(function () {
        const item = $(this);
        const idSplitted = item.attr("id").split("-");

        for (let i = 0; i < idSplitted.length; i++) {
          if (!isNaN(idSplitted[i])) {
            idSplitted[i] = self.currentIndex;
          }
        }
        const name = idSplitted.join("-");
        item.attr("name", name);
        item.attr("id", name);
      });
      self.tbody.append(newRow);

      newRow.find(".js-widget").data("cloned", true).each(Abilian.initJsWidget);

      self.currentIndex += 1;
    },
  };

  function dynamicRowWidget(params) {
    const table = $(this);
    return new DynamicRowWidget(table, params);
  }

  Abilian.registerWidgetCreator("dynamicRowWidget", dynamicRowWidget);

  $.fn.dynamicRowWidget = function (options) {
    const defaults = {};
    const opts = $.extend(defaults, options);
    return this.each(function () {
      dynamicRowWidget.bind(this)(opts);
    });
  };
});
