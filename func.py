import datetime
import time
import os
import urllib

import vk

# returns obj to access api
import wget as wget


def auth(vk_token, vk_login, vk_password):
	vk_api = None

	if vk_token:
		session = vk.AuthSession(access_token=vk_token)

		vk_api = vk.API(session)
	elif vk_login and vk_password:
		session = vk.AuthSession(
			app_id='5513659', 
			user_login = vk_login, 
			user_password = vk_password, 
			scope = 'messages,friends,audio,docs,photos,video,offline')

		vk_api = vk.API(session)

	return vk_api

# returnes if of authorized user
def me(vk_api):
	response = vk_api.users.get()
	current_id = response[0]['uid']

	return current_id

def dump_friends(vk_api, user_id):
	print('dumping friends...')
	
	friends = vk_api.friends.get(user_id=user_id, order='hints', fields='nickname')
	with open('./result/friends.txt', 'w') as f:
		for user in friends:
			f.write(
				user['first_name'] + ' ' + user['last_name'] + 
				' vk.com/id' + str(user['uid']) + 
				'\n')

	print('Done\n')

def dump_dialogs(vk_api, user_id, dphoto, count_users):
	print('dumping dialogs...')
	offset = 0

	all_dialogs = []
	while True:
		response = vk_api.messages.getDialogs(count=count_users, offset=offset)
		dialogs = response[1:]
		all_dialogs.append(dialogs)
		if len(dialogs) == 0:
			break

		if offset >= int(count_users):
			break

		path_to_res = './result'
		for dialog in dialogs:
			newpath = path_to_res
			need_sleep = False
			id_to_dump = 0
			is_multichat = False

			try:
				# if it is not multichat, will fail
				check = dialog['chat_id']

				id_to_dump = dialog['chat_id']
				is_multichat = True
				newpath += '/groups/' + dialog['title']
			except:
				# get user
				user = vk_api.users.get(user_ids=dialog['uid'])[0]
				
				newpath += '/messages/' + user['first_name'] + ' ' + user['last_name']
				id_to_dump = user['uid']

				need_sleep = True	
			finally:
				if not os.path.exists(newpath):
					os.makedirs(newpath)

			if need_sleep:
				sleep()

			dump_dialog_history(vk_api, id_to_dump, is_multichat, newpath, dphoto)

		offset += int(count_users)
		sleep()

	print('Done')

def dump_dialog_history(vk_api, user_id, is_multichat, path, dphoto):
	offset = 0
	all_messages = []
	all_user_ids = set()
	all_users = {}

	if not is_multichat:
		user = vk_api.users.get(user_ids=user_id)[0]
		all_users[user['uid']] = user

		print('	dumping history with', user['first_name'], user['last_name'] + '...')

		sleep()
	else:
		chat = vk_api.messages.getChat(chat_id=user_id)

		print('	dumping history in', chat['title'] + '...')

		# api requrement
		user_id += 2000000000
		
		sleep()

	while True:
		response = vk_api.messages.getHistory(user_id=user_id, count=200, offset = offset, rev = 1)
		messages = response[1:]
		all_messages += messages

		if len(messages) == 0:
			break

		# remember all user_ids in chat
		for message in messages:
			all_user_ids.add(message['from_id'])		

		offset += 200

		sleep()

	# map of all users in chat
	users = vk_api.users.get(user_ids=all_user_ids)
	for user in users:
		all_users[user['uid']] = user
	
	history_file = open(path + '/history.txt', 'w')
	photos_file = open(path + '/photos.txt', 'w')
	vieos_file = open(path + '/videos.txt', 'w')
	create_html_images(path, user)

	for message in all_messages:
		from_user = all_users[message['from_id']]

		date = datetime.datetime.fromtimestamp(
	        int(message['date'])
	    ).strftime('%Y-%m-%d %H:%M:%S')

		history_file.write(
			'[' + date + '] ' + 
			from_user['first_name'] + ' ' + from_user['last_name'] + ': ' 
			+ message['body'] + '\n')

		dump_attachments(vk_api, message, history_file, photos_file, vieos_file, path, dphoto)

	history_file.close()
	photos_file.close()
	vieos_file.close()
	closing_html_images(path)

def dump_attachments(vk_api, message, history_file, photos_file, vieos_file, path, dphoto):
	try:
		attatchments = message['attachments']
		for attatchment in attatchments:
			if attatchment['type'] == 'photo':
				photo_url = attatchment['photo']['src_xxbig']

				photos_file.write(photo_url + '\n')
				history_file.write(photo_url + '\n')
				if dphoto is not None:
					download_photo(path, photo_url)

				add_html_images(path, photo_url)

			elif attatchment['type'] == 'video':
				video = vk_api.video.get(videos=
					str(attatchment['video']['owner_id']) + '_' +
					str(attatchment['video']['vid']) + '_' +
					str(attatchment['video']['access_key']))[1]
					
				sleep()

				video_url = video['player']

				vieos_file.write(video_url + '\n')
				history_file.write(video_url + '\n')		
	except:

		return

def create_html_images(path, uid):
	photo_html = open(path + '/photo.html', 'w')
	str = """
	<!DOCTYPE html>
	<html>
	 <head>
	  <meta charset="utf-8">
	 </head>
	<body>
	
	<h1>Dump Photo: %s</h1>
	
	<p>Users photo</p>
	
	""" %uid

	photo_html.write(str + '\n')
	photo_html.close()


def closing_html_images(path):
	photo_html = open(path + '/photo.html', 'a')
	str = """
	</body>
	</html>

	"""
	photo_html.write(str + '\n')
	photo_html.close()


def add_html_images(path, url):
	photo_html = open(path + '/photo.html', 'a')
	str = """
	<img src="%s">

	""" %url
	photo_html.write(str + '\n')
	photo_html.close()




# default sleep time
def sleep():
	time.sleep(1)


def download_photo(path, photo_url):
	if not os.path.exists(path + '/photo'):
		os.makedirs(path + '/photo')
	file_name = photo_url[str(photo_url).rfind("/") + 1: len(photo_url)]
	newpath = path + "/photo/" + file_name
	#print(newpath)
	wget.download(photo_url, newpath)