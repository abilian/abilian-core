(function($) {
     // multiple row widget
    function DynamicRowWidget(table, options) {
        var self = this;
        self.table = table;
        self.prefix = table.data('prefix');
        self.tbody = table.children("tbody");
        self.options = options;

        self.current_index = table.find("> tbody > tr").length;

        self.add_button = $("<th><span class=\"glyphicon glyphicon-plus\"></span></th>");
        self.add_button.click(function(e) {
                                  self.addRow();
                                  e.preventDefault();
                              });

        self.minus_button = $("<td><span class=\"glyphicon glyphicon-remove\"></span></td>");
        self.minus_button.click(function(e) {
                                    $(this).closest('tr').remove();
                                    e.preventDefault();
                                });

        table.find("> thead > tr").append(self.add_button);
        table.find("> tbody > tr").append(self.minus_button);

        self.template_row = table.find("tbody > tr:first").clone(true, true);
        self.template_row.find('input[data-short-name!="csrf_token"]').attr('value', '');
        self.template_row.find("textarea").text('');
    }

    DynamicRowWidget.prototype = {
        'addRow': function() {
            var self = this;
            var new_row = self.template_row.clone(true, true);
            new_row.find("input").each(
                function() {
                    var item  = $(this);
                    var shortName = item.data("shortName");
                    var name = self.prefix + '-' + self.current_index;
                    if (shortName) {
                        name =  name + '-' + shortName;
                    }
                    item.attr('name', name);
                    item.attr("id", name);
                });
            self.tbody.append(new_row);
            new_row.find('.js-widget').each(Abilian.initJsWidget);
            self.current_index += 1;
        }
    };

    function dynamicRowWidget(params) {
        var table = $(this);
        return new DynamicRowWidget(table, params);
    }

    Abilian.registerWidgetCreator('dynamicRowWidget', dynamicRowWidget);

    $.fn.dynamicRowWidget = function(options) {
        var defaults = {};
        var opts = $.extend(defaults, options);
        return this.each(
            function() { dynamicRowWidget.bind(this)(opts); }
        );
    };

})(jQuery);
