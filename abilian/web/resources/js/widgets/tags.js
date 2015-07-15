(function(factory) {
    'use strict';
    require(['AbilianWidget', 'jquery'], factory);
}
 (function(Abilian, $) {
     'use strict';

     function initTagsSelect(params) {
         var opts = {
             multiple: true,
             separator: ';'
         };
         $.extend(opts, params);

         // as of Select2 3.5, we cannot use a <select> and
         // createSearchChoices. We must convert it to a hidden input
         var values = (this.val() || []).join(opts.separator),
             choices = $.map(this.get(0).options,
                             function(option) { return option.value; }),
             input = $('<input type="hidden" />')
                 .attr({name: this.attr('name')})
                 .val(values);

         opts.tags = choices;
         input.insertBefore(this);
         this.remove();
         return Abilian.getWidgetCreator('select2').call(input, opts);
     }

     Abilian.registerWidgetCreator('tags-select', initTagsSelect);
 }));
