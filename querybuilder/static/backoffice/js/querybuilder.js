(function(){
    String.prototype.rsplit = function(sep, maxsplit) {
        var split = this.split(sep);
        return maxsplit ? [ split.slice(0, -maxsplit).join(sep) ].concat(split.slice(-maxsplit)) : split;
    };

    var scripts = document.getElementsByTagName("script");
    var script_path = scripts[scripts.length-1].src;
    var prefix = script_path.rsplit('/', 1)[0];

    var app = angular.module('BackOfficeApp');

    app.controller('QueryBuilderController', function($scope, $filter){
        $scope.qb = {};
        var qb = $scope.qb; /* remove the .qb when we switch to controller-as */

        qb.value_choices = [];
        qb.value_choices_object = {};
        qb.query = {
            rules: [],
            page: 1
        };
        qb.editing = true;

        $scope.$watch('qb.query.rules', function(){
            qb.update_value_choices();
        }, true);
        $scope.$watch('qb.query.model', function(){
            qb.update_value_choices()
        }, false);

        $scope.view.call('get_models', {}).then(function(model_info){
            qb.model_info = model_info;
        });

        qb.new_rule = function(exclude){
            qb.query.rules.push({exclude: exclude || false});
        };

        qb.new_value = function(){
            qb.query.values.push({expression: ''});
        };

        qb.reset_rules = function(){
            qb.update_value_choices();
            qb.query.rules = [];
            qb.query.values = [];
            qb.query.page = 1;
            angular.forEach(qb.model_info.models[qb.query.model].fields, function(field, field_name){
                if (field.direct && !field.model_name && qb.query.values.length < 5) {
                    qb.query.values.push({
                        expression: field_name,
                        label: $filter('capitalize')(qb.value_choices_object[field_name].label)
                    });
                }
            });
            qb.result = {};
        };

        var get_field_choices_for_model = function(model_name, prefix){
            var choices = [];
            var model = qb.model_info && qb.model_info.models && qb.model_info.models[model_name];
            if (!model)
                return [];
            angular.forEach(model.fields, function(field, field_name){
                if (field.direct && !field.model_name) {
                    choices.push([prefix + field_name, field.label, model.verbose_name, model.name]);
                }
            });
            return choices;
        };

        qb.update_value_choices = function(){
            var choices = [];
            var models = {};
            var choices_object = {};
            models[qb.query.model] = true;
            choices.push.apply(choices, get_field_choices_for_model(qb.query.model, ''));
            angular.forEach(qb.query.rules, function(rule){
                var lookups = [''];
                var model = null;
                angular.forEach(rule.lookups, function(lookup){
                    if (lookup.model && !models[lookup.model]){
                        models[lookup.model] = true;
                        model = lookup.model;
                        lookups[0] += lookup.field + '__';
                        choices.push.apply(choices, get_field_choices_for_model(model, lookups[0]));
                    }
                });
            });
            angular.forEach(choices, function(choice){
                choices_object[choice[0]] = {
                    label: choice[1],
                    model_label: choice[2],
                    model_name: choice[3]
                };
            });

            qb.value_choices = choices;
            qb.value_choices_object = choices_object;
        };

        qb.run = function(){
            angular.forEach(qb.query.rules, function(rule){
                delete rule['errors'];
            });
            $scope.view.call('execute_query', {query: qb.query, id: qb.saved_query_id || null}).then(function(query_result){
                if (query_result.has_errors){
                    qb.query.rules = query_result.query.rules;
                }
                qb.result = query_result;
            });
        };

        qb.saved_query = {};
        qb.save_query = function(cb){
            var params = {name: qb.saved_query.name || 'untitled', query: qb.query, id: qb.saved_query.id || null};
            $scope.view.call('save_query', params).then(function(result){
                qb.saved_query = result;
                qb.saved_query_id = result.id;
                qb.fetch_saved_queries();
                qb.editing = false;
                if (cb){
                    cb(result);
                }
            });
        };

        qb.fetch_saved_queries = function(){
            $scope.view.call('get_saved_queries', {}).then(function(result){
                qb.saved_queries = result.queries;
            });
        };
        qb.fetch_saved_queries();

        qb.saved_query_id = '';
        qb.switch_saved_query = function(){
            qb.result = {};
            if (!qb.saved_query_id){
                qb.saved_query = {};
                qb.query = {rules:[]};
                qb.editing = true;
                return;
            }
            angular.forEach(qb.saved_queries, function(saved_query){
                if (saved_query.id == qb.saved_query_id){
                    qb.saved_query = saved_query;
                    qb.query = qb.saved_query.query;
                }
            });
            qb.editing = false;
        };

        qb.delete_query = function(){
            $scope.view.call('delete_query', {id: qb.saved_query.id}).then(function(){
                qb.saved_query_id = '';
                qb.switch_saved_query();
                qb.fetch_saved_queries();
            });
        };

        qb.get_header = function(value){
            if (value.label){
                return $filter('capitalize')(value.label);
            }
            var header = qb.value_choices_object[value.expression].label;
            if (value.count){
                header += ' (' + qb.model_info.strings.countText + ')'
            }
            else if (value.sum){
                header += ' (' + qb.model_info.strings.sumText + ')'
            }
            return $filter('capitalize')(header);
        };

        qb.export_to_excel = function(){
            qb.save_query(function(){
                window.location.href = $scope.view.action_link('export_to_excel', {id: qb.saved_query.id});
            });
        };
    });

    app.directive('qbRule', function(){
        return {
            templateUrl: prefix + '/rule.html',
            scope: {
                model_info: '=modelInfo',
                rule: '=qbRule',
                model: '=',
                onClickRemove: '&'
            },
            link: function(scope, elem, attrs){
                scope.make_empty_lookup = function(){
                    return {equality: '', value: ''};
                };
                if (!scope.rule.lookups || scope.rule.lookups.length == 0){
                    scope.rule.lookups = [scope.make_empty_lookup()];
                }
                scope.prev_model = function(lookup_index){
                    if (!scope.model_info)
                        return null;
                    return (lookup_index > 0
                        ? scope.rule.lookups[lookup_index-1].model
                        : scope.model);
                };
                scope.prune_lookups = function(){
                    var lookups = scope.rule.lookups;
                    for (var i = 0; i < lookups.length; i++){
                        if (!lookups[i].model && i+1 < lookups.length){
                            lookups.splice(i+1, lookups.length);
                            return;
                        }
                    }
                };
                scope.assign_model_to_lookup = function(lookup_index){
                    var lookup = scope.rule.lookups[lookup_index];
                    var prev_model = scope.prev_model(lookup_index);
                    lookup.model = scope.model_info.models[prev_model].fields[lookup.field].model_name;
                    scope.prune_lookups();
                    if (lookup.model && lookup_index == scope.rule.lookups.length - 1){
                        scope.rule.lookups.push(scope.make_empty_lookup());
                    }
                };
                scope.get_fields = function(lookup_index){
                    var prev_model = scope.prev_model(lookup_index);
                    if (!prev_model || !scope.model_info.models[prev_model])
                        return null;
                    return scope.model_info.models[prev_model].fields;
                };
                scope.get_choices = function(lookup_index){
                    var lookup = scope.rule.lookups[lookup_index];
                    var fields = scope.get_fields(lookup_index);
                    if (!fields || !lookup.field || !fields[lookup.field])
                        return null;
                    return fields[lookup.field].choices;
                };
            }
        };
    });

    app.directive('qbValue', function(){
        return {
            templateUrl: prefix + '/value_old.html',
            replace: true,
            scope: {
                value: '=qbValue',
                model_info: '=modelInfo',
                choices: '=',
                onClickRemove: '&',
                onClickInsert: '&'
            }
        };
    });

    app.directive('qTree', ['RecursionHelper', function(RecursionHelper){
        return {
            templateUrl: prefix + '/qtree.html',
            replace: true,
            scope: {'qTree': '='},
            compile: function(element){
                return RecursionHelper.compile(element);
            }
        };
    }]);

    // http://stackoverflow.com/questions/14430655/recursion-in-angular-directives
    app.factory('RecursionHelper', ['$compile', function($compile){
        return {
            /**
             * Manually compiles the element, fixing the recursion loop.
             * @param element
             * @param [link] A post-link function, or an object with function(s) registered via pre and post properties.
             * @returns An object containing the linking functions.
             */
            compile: function(element, link){
                // Normalize the link parameter
                if(angular.isFunction(link)){
                    link = { post: link };
                }

                // Break the recursion loop by removing the contents
                var contents = element.contents().remove();
                var compiledContents;
                return {
                    pre: (link && link.pre) ? link.pre : null,
                    /**
                     * Compiles and re-adds the contents
                     */
                    post: function(scope, element){
                        // Compile the contents
                        if(!compiledContents){
                            compiledContents = $compile(contents);
                        }
                        // Re-add the compiled contents to the element
                        compiledContents(scope, function(clone){
                            element.append(clone);
                        });

                        // Call the post-linking function, if any
                        if(link && link.post){
                            link.post.apply(null, arguments);
                        }
                    }
                };
            }
        };
    }]);
})();
