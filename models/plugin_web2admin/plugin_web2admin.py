a0, a1 = request.args(0), request.args(1)

def check_access(table, perm):
    return auth.is_logged_in() and \
        (auth.has_membership(role='w2a_root') or \
         (auth.has_membership(role='w2a_manager') and \
          table not in auth_tables) or \
         auth.has_permission(perm, table, 0))


@auth.requires(check_access(a0, 'w2a_delete'))
def delete_action(table, ids):
    to_delete = cdb()(cdb()[table].id.belongs(ids))
    to_delete.delete()

@auth.requires(check_access(a0, 'w2a_create'))
def clone_action(table, ids):
    t = cdb()[table]
    fields = t.fields
    to_insert = []
    for row in cdb()(t.id.belongs(ids)).select():
        to_clone = {}
        for field in fields:
            if field != t._id.name:
                to_clone[field] = row[field]
                to_insert.append(to_clone)
                t.bulk_insert(to_insert)


from gluon.tools import PluginManager
plugins = PluginManager('web2admin',
                        items_per_page = 20,
                        default_actions = {'delete':delete_action,
                                           'clone': clone_action},
                        actions = {},
                        fields = {},
                        dbs = [db],
)
plugins.web2admin.actions.update(plugins.web2admin.default_actions)

def cdb(index=-1):
    """Returns the specified database form the list or the
    currently (session) selected"""
    if index > -1:
        return plugins.web2admin.dbs[index]
    return plugins.web2admin.dbs[session.dbindex or 0]


w2a_history = cdb(0).define_table('plugin_web2admin_history',
    Field('action'),
    auth.signature
)

auth_tables = ('auth_user',
               'auth_group',
               'auth_membership',
               'auth_permission',
               'auth_event',
               'auth_cas'
)

perms = ('w2a_read',
               'w2a_create',
               'w2a_select',
               'w2a_edit',
               'w2a_delete',
               'w2a_export')


def action_dispatch(table, ids, action):
    """ This is called on selectable submit and dispatches
    the action to the right function"""
    if not ids:
        session.flash=T('Please select some rows to delete')
    else:
        if action:
            plugins.web2admin.actions[action](table,ids)
            w2a_history.insert(action=T('executed action %s on %s id(s): %s') % (action, table, ids))
        else:
            session.flash=T('Please select an action')

def history_callback(table, form, action):
    """Called on creation and updating events"""
    if action == 'deleted':
        # now form is a record_id
        w2a_history.insert(action=T('%s a %s (%s)') % (action, table, form))
        return
    format = cdb()[table]._format
    name = '(%s)' % form.vars.id
    if format:
        if callable(format): name = format(form.vars)
        else: name = format % form.vars
    w2a_history.insert(action=T('%s a %s: %s') % (action, table, name))