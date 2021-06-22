#### psuedo code for creating automated email digest

# read log file from last time script was run
#	get time stamp and other pertinent information like maybe an email_sent boolean value

# query database for all permits created after timestamp of last run
#	if no permits found, write log and exit
# database connection info:
#	- host: 165.83.50.66
#	- database: savage
#	- username: savage_read
# see https://github.com/smHooper/vistats/blob/f8780490368bed009e1e9100d5bcda0542f42b4f/py/retrieve_data.py#L422
#  for an example of connecting to and querying a DB

# compose email
#	convert query result to HTML string that can be embedded in the email message body
#		the best way to do this in my opinion is to use an HTML <table> and each
#		  row in the table corresponds to a row in the database (in this case, a permit) 
#		see https://www.w3schools.com/html/html_tables.asp for more info on HTML tables

# send email via smtplib and email libraries
#	for more on sending emails via Python see https://docs.python.org/3.9/library/email.examples.html 
#	also see https://github.com/smHooper/vistats/blob/master/py/send_notifications.py for an example implementation

# write log file
#	I suggest a JSON file because it's easy to read and write as a dictionary.
#	useful values to write to the JSON file might be:
#		- timestamp
#		- email_info:
#			- recipients
#			- message
#			- subject
#			- ...