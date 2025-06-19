##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2025, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""Code to handle data sorting in view data mode."""
import pickle
import json
from flask_babel import gettext
from flask import current_app
from pgadmin.utils.ajax import make_json_response, internal_server_error
from pgadmin.tools.sqleditor.utils.update_session_grid_transaction import \
    update_session_grid_transaction
from pgadmin.utils.exception import ConnectionLost, SSHTunnelConnectionLost
from pgadmin.utils.constants import ERROR_MSG_TRANS_ID_NOT_FOUND


class FilterDialog():
    @staticmethod
    def get(*args):
        """Fetch the current sorted columns"""
        success_flag, error_message, connection, transaction, session = args  
        
        if error_message != ERROR_MSG_TRANS_ID_NOT_FOUND: 
            pass
        else:
            return make_json_response( 
                success=0,
                errormsg=error_message,
                info='DATAGRID_TRANSACTION_REQUIRED',
                status=404
            )

        is_valid = all([  
            success_flag, 
            connection is not None,
            transaction is not None,
            session is not None
        ])

        column_names = []  
        sql_query = None  

        if is_valid:
            status_message = gettext('Success') 
            
            try:
                sorted_columns = transaction.get_all_columns_with_order()  
                column_names = []
                for col_key in session['columns_info'].keys():  
                    column_names.append(col_key)
                    
                sql_query = transaction.get_filter()
            except (ConnectionLost, SSHTunnelConnectionLost):
                raise
            except Exception as exc:  
                current_app.logger.error(exc)
                raise
        else:
            success_flag = False 
            status_message = error_message  
            sorted_columns = None 
        
        result_data = {  
            'status': success_flag,
            'msg': status_message,
            'result': {
                'data_sorting': sorted_columns,
                'column_list': column_names,
                'query': sql_query  
            }
        }
        return make_json_response(data=result_data)

    @staticmethod
    def save(*args, **kwargs):
        """To save the sorted columns"""
        # Check the transaction and connection status
        status, error_msg, conn, trans_obj, session_obj = args
        trans_id = kwargs['trans_id']
        request = kwargs['request']

        if request.data:
            data = json.loads(request.data)
        else:
            data = request.args or request.form

        if error_msg == ERROR_MSG_TRANS_ID_NOT_FOUND:
            return make_json_response(
                success=0,
                errormsg=error_msg,
                info='DATAGRID_TRANSACTION_REQUIRED',
                status=404
            )

        if status and conn is not None and \
           trans_obj is not None and session_obj is not None:
            trans_obj.set_data_sorting(data, True)
            status, res = trans_obj.set_filter(data.get('sql'))
            if status:
                # As we changed the transaction object we need to
                # restore it and update the session variable.
                session_obj['command_obj'] = pickle.dumps(trans_obj, -1)
                update_session_grid_transaction(trans_id, session_obj)
                res = gettext('Data sorting object updated successfully')
        else:
            return internal_server_error(
                errormsg=gettext('Failed to update the data on server.')
            )

        return make_json_response(
            data={
                'status': status,
                'result': res
            }
        )
