# Imports
import json
import datetime
import sqlalchemy
import smtplib
from email.mime import text as mimetext, multipart as mimemultipart
import pandas as pd
import dateutil
import sys
import os


# funcs
# takes in a dictionary and writes it to a json log file
def write_to_log(log_info,directory):
    log_path = os.path.join(directory, f"savage_permit_log_file{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_path,"w") as log_file:
        json.dump(log_info,log_file,indent=4)


# runs when script try block is exited, prints error info into log file
def write_to_log_error(error_type,params,directory, email_sent=False,html_content="email content was not created"):
    error_info= {'Error':f"Script did not finish, {error_type}"}
    error_info['intended email recipient'] = params["email_credentials"]["recipient_email"]
    error_info['email sent'] = email_sent
    error_info['html content'] = html_content
    log_path = os.path.join(directory, f"savage_permit_log_file{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(log_path,"w") as log_file:
        json.dump(error_info,log_file,indent=8)


#  turns a data frame into html email string
def get_html_table(data, column_widths={}):
    thead_tr_style = 'style="font-weight: bold; height: 40px; background-color: #cccccc;'
    cell_style = 'style="padding-left: 20px; padding-right: 20px;"'
    thead_html = ('<tr {tr_style}"><th {cell_style}>' + '</th><th {cell_style}>'.join(data.columns) + '</th></tr>') \
        .format(tr_style=thead_tr_style, cell_style=cell_style)
    tr_bg_dark = ' background-color: #f2f2f2;'
    tr_content = data.apply(
        lambda x: ('<td {cell_style}>' + '</td><td {cell_style}>'.join(x.astype(str)) + '</td>').format(
            cell_style=cell_style),
        axis=1)
    tbody_html = ''.join(['<tr style="height: 40px; {bg_style}">{td_elements}'.format(
        bg_style=tr_bg_dark if i % 2 == 1 else '', td_elements=td_elements, cell_style=cell_style) for i, td_elements in
        tr_content.items()]) + '</tr>'

    for column_name, width in column_widths.items():
        thead_html.replace('<th {cell_style}>{column}</th>'.format(cell_style=cell_style, column=column_name),
                           '<th {cell_style}>{column}</th>'.format(
                               cell_style=cell_style.replace(';"', '; min-width:%s;"' % width), column=column_name))
    html = \
        """<p> Below is a table of the most recent NPS Contractor Park Road Permits that were granted. </p> <table style="border-spacing: 0px;"><thead>{table_header} </thead><tbody>{table_body}</tbody></table>""".format(table_header=thead_html, table_body=tbody_html)
    return html


# takes in html content/email server/email info and sends the html table email
def send_email(html_content, server_name, port, sender, recipient, subject):
    # Create message
    msg = mimemultipart.MIMEMultipart('mixed')
    msg.add_header('Content-Type', 'text/html')
    msg_content = mimetext.MIMEText(html_content, 'html', 'utf-8')
    msg.attach(msg_content)
    msg['Subject'] = subject
    # sending to/from
    msg['From'] = sender
    msg['To'] = recipient

    # need to create server
    server = smtplib.SMTP(server_name,port)
    server.starttls()
    server.ehlo()
    # send message via server
    server.send_message(msg)

def main(param_path):
    try:
        # email hasnt sent yet, updates if script runs through the sending portion
        html_email_sent = False
        ## access to savage_permit_params
        # param_path = r'C:\Users\bnbrown\savage_permits\savage_nongit\savage_permit_params.json'
        with open(param_path) as f:
            params = json.load(f)
        # creates engine
        engine = sqlalchemy.create_engine(
                    'postgresql://{username}:{password}@{ip_address}:{port}/{db_name}'.format(**params['savage_permit_db_params']))
        # makes code only send entries from last 2 weeks
        last_time_entered = (datetime.datetime.now() - dateutil.relativedelta.relativedelta(days=14)).strftime('%Y-%m-%d %H:%M')
        # creates a dataframe of only the info we need
        relevant_info = pd.read_sql('''select time_entered,date_in,date_out,entered_by, permit_number, permit_holder,
             destination, id from road_permits where permit_type = 'Contractor-NPS' and time_entered > '{last_time_entered}' and (not was_emailed or was_emailed IS null) order by id desc
              '''.format(last_time_entered=last_time_entered), engine)
        if len(relevant_info) == 0:
            no_data_dict = {}
            no_data_dict['timestamp'] = datetime.datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
            no_data_dict['reason for not sending'] = 'no permits were input over the last 2 weeks'
            write_to_log(no_data_dict,params['log_file_directory'])
            return
        # rename titles in a cleaner way
        new_column_names = {"time_entered":"Time Entered","permit_number":"Permit Number","permit_holder":"Permit Holder","destination":"Destination","date_in":"Date In","date_out":"Date Out","entered_by":"Entered By"}
        relevant_info_cleaned = relevant_info.rename(columns=new_column_names).drop(relevant_info.columns[~relevant_info.columns.isin(new_column_names)],axis=1)

        # get html formatted email
        html_email = get_html_table(relevant_info_cleaned)
        # Send Email
        # need to change from my email to a different recipient
        send_email(html_email,params["mail_server_credentials"]["server_name"],params["mail_server_credentials"]["port"],"Savage_Permits <Savage_Permit_No_Reply@nps.gov>",params["email_credentials"]["recipient_email"],'Savage Road Permits Update')
        html_email_sent = True
        # write to log file
        ids_to_update = ','.join(relevant_info.id.astype(str))
        relevant_info_json_compatible = relevant_info.drop(["date_in", "date_out","time_entered","entered_by","permit_number","permit_holder","destination"],axis=1)
        relevant_info_json = {}
        relevant_info_json['email recipient'] = params["email_credentials"]["recipient_email"]
        relevant_info_json['timestamp'] = datetime.datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)")
        relevant_info_json['HTML Email'] = html_email
        relevant_info_json['email sent'] = html_email_sent
        relevant_info_json['permit ids'] = ids_to_update
        write_to_log(relevant_info_json,params['log_file_directory'])

        #### updates the database -was_emailed- column

        # print(ids_to_update)
        engine.execute(f'''UPDATE road_permits SET was_emailed=True WHERE id IN ({ids_to_update})''')

    except sqlalchemy.exc.ProgrammingError:
        write_to_log_error('ProgrammingError : check road_permit admin permissions',params,params['log_file_directory'],html_email_sent,html_email)

    except Exception as e:
        write_to_log_error(e,params,params['log_file_directory'],html_email_sent,html_email)

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))