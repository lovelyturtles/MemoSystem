import sys
import socket
import threading
import memodb
import uuid
import json
import os

HOST = ''
PORT = 8265
FORMAT = 'utf-8'
ADDRESS = (HOST, PORT)

HTTP_VERSION = 'HTTP/1.1'
HTTP_SUCCESS = '200 OK'
HTTP_CREATED = '201 Created'


def request_to_dict(request):
    # remove leading and trailing newlines
    request = request.strip()
    # replace the newlines in the string with ": " to make it easier to parse
    request = request.replace("\r\n", ": ")
    request = request.split(": ")

    # now turn the list into dict
    i = iter(request)
    request_dict = dict(zip(i, i))
    return request_dict


def not_authorized():
    status_line = HTTP_VERSION + ' 401 Unauthorized'
    content_length = 'Content-Length: 0'
    return '{}\r\n{}\r\n\r\n'.format(status_line, content_length)


def bad_request():
    return HTTP_VERSION + ' 400 Bad Request\r\nContent-Length: 0\r\n\r\n'


def not_found():
    return HTTP_VERSION + ' 404 Not Found\r\nContent-Length: 0\r\n\r\n'


def not_allowed():
    return HTTP_VERSION + ' 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n'


def not_supported():
    return HTTP_VERSION + ' 505 HTTP Version Not Supported\r\nContent-Length: 0\r\n\r\n'


def server_error():
    return HTTP_VERSION + ' 500 Internal Server Error\r\nContent-Length: 0\r\n\r\n'


def response_header_template(status_code, response_body):
    # response header contents
    status_line = '{} {}'.format(HTTP_VERSION, status_code)
    content_length = 'Content-Length: {}'.format(len(response_body))
    content_type = 'Content-Type: application/json'
    more_access = 'Access-Control-Allow-Origin: *'
    access_control = 'Access-Control-Allow-Origin: localhost:8265/'

    return '{}\r\n{}\r\n{}\r\n{}\r\n{}'.format(status_line, content_length, content_type, more_access, access_control)


def cookie_header(connection, header_template):
    response_header = None

    session_id = str(uuid.uuid4())
    # add the session id to the database
    add_session = memodb.add_session(connection, session_id)

    # if the ID was added to the database, we'll send it to the client
    if add_session is not None:
        set_cookie = 'Set-Cookie: session_id={}'.format(session_id)
        response_header = '{}\r\n{}'.format(header_template, set_cookie)

    return response_header


def find_session_id(connection, all_cookies):
    found = None
    failed_query = 0
    cookies = all_cookies.split("; ")
    keep_searching = 1
    for cookie in cookies:
        if keep_searching:
            split_cookie = cookie.split("=")
            cookie_value = split_cookie[1]  # this holds the actual session id value

            # check if the Cookie is in our database
            check_id = memodb.get_session_by_id(connection, cookie_value)
            # make sure an error wasn't thrown

            if check_id is not None:

                # if the list that's returned isn't empty, the ID is in the database
                # and we can stop the loop. if not, keep searching
                if check_id:
                    found = [1, cookie_value]
                    keep_searching = 0

            # if check_id is None, something went wrong querying the database
            else:
                keep_searching = 0
                failed_query = 1

    if found is None and failed_query == 0:
        found = [0, '']

    return found


def get_api(connection, path, remaining_request):
    # default values
    response = bad_request()  # if the path list has more than 1 value, this is a bad request
    response_body = ''

    # otherwise
    if len(path) == 1:
        # we only deal with memos in this API
        if path[0] == 'memos':

            # get all the memos from the database
            memo_rows = memodb.get_all_memos(connection)

            # make sure there wasn't an error completing this query
            if memo_rows is not None:

                # check if the memo table is empty or not
                if memo_rows:
                    memo_keys = ['memo_id', 'content', 'last_edited_by']
                    response_body = memodb.to_dict_json(memo_keys, memo_rows)

                # if the memo table is empty, so is our response_body.
                # this is the default value for response_body so we
                # don't have to do anything

                # now that we have our response body, deal with the response header
                header_template = response_header_template(HTTP_SUCCESS, response_body)

                # if the request header doesn't have a tracking Cookie
                if 'Cookie' not in remaining_request:

                    response_header = cookie_header(connection, header_template)

                    if response_header is not None:
                        response = '{}\r\n\r\n{}'.format(response_header, response_body)

                    # if we couldn't add the ID for whatever reason, our bad
                    else:
                        response = server_error()

                # if the request header has a tracking Cookie
                else:
                    # get the Cookie from the request header and check if it's in our database
                    found = find_session_id(connection, remaining_request['Cookie'])

                    # if found is None there was a server error
                    if found is None:
                        response = server_error()

                    # if not none, we can check if the id was in the database
                    else:

                        # if we found the id in the database, don't need to set a tracking cookie
                        if found[0]:
                            response = '{}\r\n\r\n{}'.format(header_template, response_body)

                        # if we didn't find the id in our database, set our own tracking cookie
                        else:
                            response_header = cookie_header(connection, header_template)

                            if response_header is not None:
                                response = '{}\r\n\r\n{}'.format(response_header, response_body)

                            # if we couldn't add the ID for whatever reason, our bad
                            else:
                                response = server_error()

            else:
                response = server_error()

        else:
            response = not_found()

    return response


def post_api(connection, path, remaining_request, body):
    # if the request header doesn't have a Cookie, they're not authorized to make a POST
    response = not_authorized()
    print(path)
    print(body)
    # otherwise
    if 'Cookie' in remaining_request:
        if len(path) == 1:
            if path[0] == 'memos':
                body_dictionary = json.loads(body)
                body_key = next(iter(body_dictionary))  # get the key for the message
                content = body_dictionary[body_key]

                found = find_session_id(connection, remaining_request['Cookie'])

                # if found is None, there was a server error
                if found is None:
                    response = server_error()

                # if not none, we can check if the id was in the database
                else:

                    # if we found the id in the database, we can add the memo
                    if found[0]:
                        add_memo = memodb.add_memo(connection, content, found[1])
                        if add_memo is not None:
                            # blank response body. nothing really to say
                            response_body = ''
                            response_header = response_header_template(HTTP_CREATED, response_body)
                            # now we can bring it all together to form the response
                            response = '{}\r\n\r\n{}'.format(response_header, response_body)

                        # if the memo couldn't be added for whatever reason, server error (our fault)
                        else:
                            response = server_error()

                    # if we didn't find the id in our database, they're not authorized to post
                    else:
                        response = not_authorized()

            else:
                response = not_found()

        else:
            response = bad_request()

    return response


def put_api(connection, path, remaining_request, body):
    # if the request header doesn't have a Cookie, they're not authorized to update
    response = not_authorized()

    if 'Cookie' in remaining_request:

        if len(path) == 2:

            if path[0] == 'memos':

                memo_id = int(path[1])

                # check if their cookie is in our database
                found = find_session_id(connection, remaining_request['Cookie'])

                # if found is None, there was a server error
                if found is None:
                    response = server_error()

                # if not none, we can check if the id was in the database
                else:

                    # if we found their id in the database, they're authorized to update
                    if found[0]:

                        # now we can check if the memo they want is in the database
                        get_memo = memodb.get_memo_by_id(connection, memo_id)

                        # if the memo id is in our database this will be true.
                        # (python returns true if non-empty list)
                        if get_memo:

                            # now we can start constructing our response.

                            # empty response body because we don't have anything to say
                            response_body = ''

                            # get the message from the request body
                            body_dictionary = json.loads(body)
                            body_key = next(iter(body_dictionary))  # get the key for the message
                            content = body_dictionary[body_key]

                            update = memodb.update_memo_by_id(connection, memo_id, found[1], content)

                            # if the update was successful, tell the client
                            if update == 1:
                                response = response_header_template(HTTP_SUCCESS, response_body)

                            # otherwise, there was some issue with the database (our fault)
                            else:
                                response = server_error()

                        # if the memo id isn't in our database, 404
                        else:
                            response = not_found()

                    # if we didn't find their id in our database, they're not authorized to update
                    else:
                        response = not_authorized()

            # if the first value isn't "memo" we don't have it
            else:
                response = not_found()

        # if the path doesn't have exactly 2 elements, this is a bad request
        else:
            response = bad_request()

    return response


def delete_api(connection, path, remaining_request):
    # if the request header doesn't have a Cookie, they're not authorized to update
    response = not_authorized()

    if 'Cookie' in remaining_request:

        if len(path) == 2:

            if path[0] == 'memos':

                memo_id = int(path[1])

                # check if their cookie is in our database
                found = find_session_id(connection, remaining_request['Cookie'])

                # if found is None, there was a server error
                if found is None:
                    response = server_error()

                # if not none, we can check if the id was in the database
                else:

                    # if we found their id in the database, they're authorized to update
                    if found[0]:

                        # now we can check if the memo they want is in the database
                        get_memo = memodb.get_memo_by_id(connection, memo_id)

                        # if the memo id is in our database this will be true.
                        # (python returns true if non-empty list)
                        if get_memo:

                            # now we can start constructing our response.

                            # empty response body because we don't have anything to say
                            response_body = ''

                            delete_memo = memodb.delete_memo_by_id(connection, memo_id)
                            # if the memo was deleted, send an OK message
                            if delete_memo == 1:
                                response = response_header_template(HTTP_SUCCESS, response_body)

                            # if the memo deletion failed, server error
                            else:
                                response = server_error()

                        # if the memo id isn't in our database, 404
                        else:
                            response = not_found()

                    # if we didn't find their id in our database, they're not authorized to update
                    else:
                        response = not_authorized()

            # if the first value isn't "memo", we don't have it
            else:
                response = not_found()

        # if we don't have exactly 2 elements in the path, this is a bad request
        else:
            response = server_error()

    return response


def handle_api(database_conn, verb, path, remaining_request, body):
    # at this point we've made sure the verb is one of the 4
    # so if something goes wrong, it's on us
    response = server_error()
    if verb == "GET":
        response = get_api(database_conn, path, remaining_request)
    elif verb == "POST":
        response = post_api(database_conn, path, remaining_request, body)
    elif verb == "PUT":
        response = put_api(database_conn, path, remaining_request, body)
    elif verb == "DELETE":
        response = delete_api(database_conn, path, remaining_request)

    return response


def file_header_template(cont_length, cont_type):
    status_line = '{} {}'.format(HTTP_VERSION, HTTP_SUCCESS)
    content_type = 'Content-Type: {}'.format(cont_type)
    content_length = 'Content-Length: {}'.format(cont_length)
    return '{}\r\n{}\r\n{}'.format(status_line, content_type, content_length)


def get_file_info(root, folder_type, search_name):
    result = None

    path_name = ''

    # default type is
    content_type = 'text/plain; charset=us-ascii'

    keep_reading = 1

    # loop through all the files in the current file or directory and see if ours is there
    for name in folder_type:
        # keep reading until we find our file
        if keep_reading:

            path_name = os.path.join(root, name)
            file_name = name  # the name we're going to compare search_name to
            extension = os.path.splitext(name)[1]

            # if we find our file
            if file_name == search_name:

                keep_reading = 0
                # if the file extension is some kind of image, content_type = image/something
                if extension == '.jpeg' or extension == '.png' or extension == '.jpg' or extension == '.ico':

                    if extension == '.jpeg' or extension == '.jpg':
                        content_type = 'image/jpeg'

                    elif extension == '.png':
                        content_type = 'image/png'

                    else:
                        content_type = 'image/vnd.microsoft.icon'

                # otherwise, the file is gonna be html or something else
                else:
                    if extension == '.html':
                        content_type = 'text/html'

    if not keep_reading:
        result = [path_name, content_type]

    return result


# this returns the pathname of the file we're looking for as well as
# the content type of that file
# if the file wasn't found, response is null
def file_search(search_name, working_directory):
    response = None

    keep_reading = 1
    for root, directories, files in os.walk(working_directory):
        if keep_reading:
            response = get_file_info(root, files, search_name)
            if response is not None:
                keep_reading = 0
            # if the correct file wasn't found, check the directories
            else:
                response = get_file_info(root, directories, search_name)

    return response


def respond_and_close(response, socket_conn, database_conn):
    # print(response)
    # send the response over the socket
    socket_conn.sendall(response.encode(FORMAT))
    # now we're done, we can close the database connection
    database_conn.close()
    # now we're done, close the current socket connection
    socket_conn.close()


# this will also take the socket connection and the database connection
def handle_file(socket_conn, database_conn, method, path):
    # the file will be the last element in the array
    file_name = path[len(path) - 1]
    # otherwise, see if we can find the file and such
    if method == 'GET':

        # get our current working directory
        file_path = os.getcwd()
        # search for the filename in the current working directory
        # we get the pathname of the file and the content type
        file_info = file_search(file_name, file_path)
        if file_info is None:
            respond_and_close(not_found(), socket_conn, database_conn)

        else:
            content_type = file_info[1]
            if file_info[1] == 'image/jpeg' or file_info[1] == 'image/png' or file_info == 'image/vnd.microsoft.icon':
                content_length = os.stat(file_info[0]).st_size
                response_header = file_header_template(content_length, content_type)
                f = open(file_info[0], "rb")
                send_response_header = '{}\r\n\r\n'.format(response_header)
                # send the header and the binary body separately
                socket_conn.sendall(send_response_header.encode(FORMAT))
                # send the binary directly
                socket_conn.sendall(f.read())
                # now we're done, we can close the database connection
                database_conn.close()
                # now we're done, close the current socket connection
                socket_conn.close()
                f.close()
            else:
                f = open(file_info[0])
                line = f.readline()
                response_body = line
                while line:
                    response_body += '{}\r\n'.format(line.rstrip())
                    line = f.readline()
                response_header = file_header_template(len(response_body), content_type)
                response = '{}\r\n\r\n{}'.format(response_header, response_body)
                respond_and_close(response, socket_conn, database_conn)
                f.close()

    else:
        # if the type of method isn't GET, it's not allowed
        respond_and_close(not_allowed(), socket_conn, database_conn)


def initialize_db(connection):
    # create the table of sessionIDs if it doesn't exist
    sessions_statement = memodb.create_sessions_statement()
    memodb.create_table(connection, sessions_statement)

    # create the table of memos if it doesn't exist
    memos_statement = memodb.create_memo_statement()
    memodb.create_table(connection, memos_statement)


def handle_client(socket_conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    # start up the database connection
    database_conn = memodb.create_connection("memoSystem.db")

    if database_conn is None:
        print("Error! Could not create the database connection.\n")
        # # send the response over the socket
        # socket_conn.sendall(server_error().encode(FORMAT))
        # # now we're done, we can close the database connection
        # # now we're done, close the current socket connection
        socket_conn.close()

    else:
        initialize_db(database_conn)
        try:
            data = socket_conn.recv(1024).decode(FORMAT)

            # split the request into header and body
            split_header_body = data.partition("\r\n\r\n")  # [0] request, [1]: \r\n\r\n, [2]: body

            # separate the request line from the rest of the request
            split_request = split_header_body[0].split("\r\n", 1)
            request_line = split_request[0]
            remaining_request = request_to_dict(split_request[1])
            # initialize the response body to blank
            body = ''

            # print(split_header_body[0])

            if 'Content-Length' in remaining_request and int(remaining_request['Content-Length']) > 0:
                body = split_header_body[2]

            # split the GET from the path from the HTTP version
            split_request_line = request_line.split(" ")
            method = split_request_line[0].strip()
            path = split_request_line[1].strip()
            version = split_request_line[2].strip()

            # make sure they're using version 1.1
            version_number = version.split("/")[1]
            if version_number != '1.1':
                respond_and_close(not_supported(), socket_conn, database_conn)

            else:

                # check if they have the right method
                if method != "GET" and method != "POST" and method != "PUT" and method != "DELETE":
                    respond_and_close(bad_request(), socket_conn, database_conn)

                else:
                    # make sure this is actually a path
                    if path[0] == "/":
                        path_tokens = path[1:].split("/")
                        # print(path_tokens)
                        if path_tokens[0] == "api":
                            response = handle_api(database_conn, method, path_tokens[1:], remaining_request, body)
                            respond_and_close(response, socket_conn, database_conn)

                        # if it's not an api request, open the files
                        else:

                            if path == '/':
                                handle_file(socket_conn, database_conn, method, ['index.html'])
                            else:
                                handle_file(socket_conn, database_conn, method, path_tokens)

                    else:
                        respond_and_close(bad_request(), socket_conn, database_conn)

        except Exception:
            respond_and_close(server_error(), socket_conn, database_conn)


# start listening for connections and then pass them to handle_client which will run in a new thread
def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(ADDRESS)
    # server.settimeout(10)  # you have 10 seconds to respond
    server.listen()
    print(f"[LISTENING] Server is listening on {HOST}")
    # we'll keep listening forever
    while True:
        try:
            conn, addr = server.accept()  # blocking code
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[NUMBER OF THREADS] {threading.active_count() - 1}")

        # except socket.timeout:
        #     print("timed out...\n")

        except KeyboardInterrupt:
            print("Bye!")
            server.close()
            sys.exit(0)

        except Exception as e:
            print("Something bad happened!\n")
            print(e)


def main():
    print("[STARTING] server is starting...")
    start()


main()
