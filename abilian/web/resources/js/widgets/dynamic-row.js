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
        if (self.options == null){self.options = 'top'};
        self.currentIndex = table.find('> tbody > tr').length;
        self.table.addClass('dynamic-row-widget');
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
        if(self.options.indexOf('top') > -1){
          table.find('> thead > tr').append(self.addButton);
        }
        if(self.options.indexOf('bottom') > -1){
          var bottom_addButton = self.addButton.clone();
          bottom_addButton.click(function(e) {
                                  self.addRow();
                                  e.preventDefault();
                              });
          table.find('> tfoot > tr').append(bottom_addButton);
        }
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
            var newRow = self.templateRow.clone(true, true);
            newRow.find('input').each(
                function() {
                    var item  = $(this);
                    var shortName = item.data('shortName');
                    var name = self.prefix + '-' + self.currentIndex;
                    if (shortName) {
                        name =  name + '-' + shortName;
                    }
                    item.attr('name', name);
                    item.attr('id', name);
                });
            newRow.find('select').each(
                function() {
                    var item  = $(this);
                    var idSplitted = item.attr('id').split('-');

                    for (var i = 0; i < idSplitted.length; i++) {
                        if (!isNaN(idSplitted[i])){
                            idSplitted[i] = self.currentIndex;
                        }
                    }
                    var name = idSplitted.join('-');
                    item.attr('name', name);
                    item.attr('id', name);
                }
            );
            self.tbody.append(newRow);

            newRow.find('.js-widget')
                .data('cloned', true)
                .each(Abilian.initJsWidget);

            self.currentIndex += 1;
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
