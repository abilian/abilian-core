(function(factory) {
    'use strict';
    require(['AbilianWidget', 'jquery'], factory);
}
 (function(Abilian, $) {
     'use strict';
     // multiple row widget
    function DynamicRowWidget(table, options) {
        var self = this;
        self.table = table;
        self.prefix = table.data('prefix');
        self.tbody = table.children('tbody');
        self.options = options;

        self.current_index = table.find('> tbody > tr').length;

        self.addButton = $('<th><span class="glyphicon glyphicon-plus"></span></th>');
        self.addButton.css({'width': '1em'});
        self.addButton.click(function(e) {
                                  self.addRow();
                                  e.preventDefault();
                              });

        self.minusButton = $('<td><span class="glyphicon glyphicon-remove"></span></td>');
        self.minusButton.click(function(e) {
                                    $(this).closest('tr').remove();
                                    e.preventDefault();
                                });

        table.find('> thead > tr').append(self.addButton);
        table.find('> tbody > tr').append(self.minusButton);

        self.templateRow = table.find('tbody > tr:first').clone(true, true);
        /* remove value except for specific controls that have constant (and
         * required) value
         */
        self.templateRow.find('input' +
                               '[type!="checkbox"]' +
                               '[type!="radio"]' +
                               '[data-short-name!="csrf_token"]')
            .attr('value', '');
        self.templateRow.find('textarea').text('');
    }

    DynamicRowWidget.prototype = {
        'addRow': function() {
            var self = this;
            var new_row = self.templateRow.clone(true, true);
            new_row.find('input').each(
                function() {
                    var item  = $(this);
                    var shortName = item.data('shortName');
                    var name = self.prefix + '-' + self.current_index;
                    if (shortName) {
                        name =  name + '-' + shortName;
                    }
                    item.attr('name', name);
                    item.attr('id', name);
                });
            new_row.find('select').each(
                function() {
                    var item  = $(this);
                    var id_splitted = item.attr('id').split('-');

                    for (var i = 0; i < id_splitted.length; i++) {
                        if (!isNaN(id_splitted[i])){
                            id_splitted[i] = self.current_index
                        }
                    }
                    var name = id_splitted.join('-')
                    item.attr('name', name);
                    item.attr('id', name);
                }
            );
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

}));
