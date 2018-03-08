# coding = utf-8
import os
import re
from os.path import join
import codecs
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import sys
import ConfigParser

def open_type_file(file_path, file_type):
    file_list = []
    for root, dirs, files in os.walk(file_path):
        for single_file in files:
            if re.search(file_type, single_file):
                file_full_name = join(root, single_file)
                file_list.append(file_full_name)
    return file_list

def open_all_file(file_path):
    file_list = []
    for root, dirs, files in os.walk(file_path):
        for OneFileName in files:
            if re.search(r'files_check_results', OneFileName) is None:
                OneFullFileName = join(root, OneFileName)
                file_list.append(OneFullFileName)
    return file_list

def open_none_svn_dir_files(file_path):
    all_file_list = open_all_file(file_path)
    none_svn_dir_files = []
    for single_file in all_file_list:
        if re.search(r'\.svn', single_file) is None:
            none_svn_dir_files.append(single_file)
    return none_svn_dir_files

# Checkout the code from SVN.
def svn_checkout(svn_path, svn_revision, svn_admin, svn_repository, svn_repository_folder, changed_paths_list, changed_files_list):
    os.mkdir(svn_path)
    os.chdir(svn_path)
    svn_checkout_pa = 1
    svn_up_pa = 1
    for changed_path in changed_paths_list:
        if changed_path == svn_repository_folder:
            svn_depth_command = '%s%s%s%s%s%s%s%s%s%s'%('svn checkout --depth=empty file://', svn_repository, ' -r ', str(svn_revision), ' ', svn_repository_folder, ' --username ', svn_admin[0], ' --password ', svn_admin[1])
        else:
            svn_depth_command = '%s%s%s%s%s%s%s%s%s%s%s%s'%('svn checkout --depth=empty file://', svn_repository, '/', changed_path, ' -r ', str(svn_revision), ' ', changed_path, ' --username ', svn_admin[0], ' --password ', svn_admin[1])
        try:
            os.system(svn_depth_command)
        except:
            svn_checkout_pa = -1
    svn_checkout_path = open_all_dirs(svn_path)
    for single_co_path in svn_checkout_path:
        for changed_file in changed_files_list:
            if len(changed_file.split('/')) > 1:
                changed_file_path = '/'.join(changed_file.split('/')[:-1])
            else:
                changed_file_path = svn_repository_folder
            if single_co_path.split(svn_path)[-1].replace('/','') == changed_file_path.replace('/',''):
                os.chdir(single_co_path)
                svn_up_command = '%s%s%s%s%s%s%s%s'%('svn up ', changed_file.split('/')[-1], ' -r ', svn_revision, ' --username ', svn_admin[0], ' --password ', svn_admin[1])
                try:
                    os.system(svn_up_command)
                except:
                    svn_up_pa = -1
                    continue
    return svn_checkout_pa, svn_up_pa

def build_patched_file_api_url(review_board_url, review_id, diffs_id_list, files_id_list, review_board_admin):
    patched_file_api_url = []
    for diff_id in diffs_id_list:
        for file_id in files_id_list:
            url_combination = '%s%s%s%s%s%s%s%s%s%s%s%s'%('http://', review_board_url, '/api/review-requests/', str(review_id), '/diffs/', str(diff_id), '/files/', str(file_id), '/patched-file/ --user ', review_board_admin, 'match_id', str(file_id))
            patched_file_api_url.append(url_combination)
    return patched_file_api_url

def patched_file_id_match(file_path):
    id_and_patch = []
    patched_match_id_json = open_type_file(file_path, r'files_id_\d+.json')
    for single_json in patched_match_id_json:
        fp_match_id = codecs.open(single_json, 'r', 'GBK')
        match_id_content = fp_match_id.read()
        part_content = match_id_content.split('dest_file')
        for single_part in part_content:
            file_id_match = re.search(r'files\/\d+\/patched-file', single_part)
            patched_file_name = re.search(r'source_file[\s\S]*\,', single_part)
            if file_id_match is not None and patched_file_name is not None:
                id_name_match = patched_file_name.group()[15:len(patched_file_name.group())-2] + '{{' + str(re.search('\d+', file_id_match.group()).group())
                id_and_patch.append(id_name_match)
    return id_and_patch

def create_patched_files_dirs(file_path, id_and_patched_list, svn_repository_folder):
    patched_path = '%s%s'%(file_path, 'patch_file/')
    if os.path.exists(patched_path):
        shutil.rmtree(patched_path)
    os.mkdir(patched_path)
    adjust_id_and_patched = []
    patched_file_dirs = []
    for single_match in id_and_patched_list:
        if len(single_match.split(svn_repository_folder)) > 1:
            adjust_id_and_patched.append(''.join(single_match.split(svn_repository_folder)[1:]))
        else:
            adjust_id_and_patched.append(single_match)
    for single_adjust in adjust_id_and_patched:
        if single_adjust[0] == '/':
            single_adjust_d = single_adjust[1:]
        else:
            single_adjust_d = single_adjust
        if len(single_adjust_d.split('/')) > 1:
            patched_file_dirs.append('/'.join(single_adjust_d.split('/')[:-1]))
        else:
            patched_file_dirs.append(svn_repository_folder)
    patched_file_dirs_c = list(set(patched_file_dirs))
    for single_dir in patched_file_dirs_c:
        os.makedirs('%s%s'%(patched_path, single_dir))
    return adjust_id_and_patched

# Download the file from Reviewboard
def get_patch_file(file_path, api_url_list, adjust_id_and_patched_list, svn_repository_folder):
    patched_path = '%s%s' % (file_path, 'patch_file/')
    adjust_dir_name_list = []
    get_patch_file_pa = 1
    for single_id_patch in adjust_id_and_patched_list:
        if single_id_patch[0] == '/':
            single_id_df = single_id_patch[1:]
        else:
            single_id_df = single_id_patch
        if len(single_id_df.split('/')) > 1:
            single_id_dir = single_id_df
        else:
            single_id_dir = '%s%s%s'%(svn_repository_folder, '/', single_id_df)
        adjust_dir_name_list.append(single_id_dir)
    for single_api_url in api_url_list:
        for adjust_dir in adjust_dir_name_list:
            if re.search(adjust_dir.split('{{')[-1], single_api_url.split('match_id')[-1]) is not None:
                single_dir_name = adjust_dir.split('{{')[-2]
                single_dir = '/'.join(single_dir_name.split('/')[:-1])
                os.chdir(patched_path + single_dir)
                get_patch_command = '%s%s%s%s'%('curl ', single_api_url.split('match_id')[-2], '> ', single_dir_name.split('/')[-1])
                try:
                    os.system(get_patch_command)
                except:
                    get_patch_file_pa = -1
                    continue
    return adjust_dir_name_list, get_patch_file_pa

# Some files will have BOM char in Linux, delete.
def remove_BOM(file):
    BOM = b'\xef\xbb\xbf'
    exist_BOM = lambda strg: True if strg == BOM else False
    fp_file = open(file, 'rb')
    if exist_BOM(fp_file.read(3)):
        file_content = fp_file.read()
        with open(file, 'wb') as f:
            f.write(file_content)
    fp_file.close()

# Use diff tool to make difference.
def create_diff_txt(file_path, svn_path, svn_repository_folder):
    patch_path = '%s%s'%(file_path, 'patch_file/')
    diff_between_two = '%s%s'%(file_path, 'diff_between_svn_and_RB/')
    os.mkdir(diff_between_two)
    ori_list = open_all_file(svn_path)
    patch_list = open_all_file(patch_path)
    diff_txt_path = '%s%s'%(file_path, 'diff.txt')
    diff_txt = open(diff_txt_path, 'w')
    index = 0
    os.chdir(file_path)
    for single_patch in patch_list:
        try:
            remove_BOM(single_patch)
        except:
            continue
    os.chdir(diff_between_two)
    for patch in patch_list:
        for ori in ori_list:
            if unicode(patch.split(patch_path)[-1].replace('/',''), 'GBK') == unicode(ori.split(svn_path)[-1].replace('/', ''), 'GBK'):
                index += 1
                change_format_to_unix_command = '%s%s%s%s'%('dos2unix -k -n ', ori, ' ', ori)
                os.system(change_format_to_unix_command)
                diff_between_two_command = '%s%s%s%s%s%s%s'%('diff ', ori, ' ', patch, ' > ', ori[1:].replace('/','{{'), '.patch')
                os.system(diff_between_two_command)
    create_diff_between_two = open_type_file(diff_between_two, r'\.patch')
    for single_diff_file in create_diff_between_two:
        if os.path.getsize(single_diff_file):
            diff_txt.write('\n' + single_diff_file.split('/')[-1][:-6].replace('{{', '/') + '; ')
    diff_txt.close()
    return index

def create_information_json(file_path, review_board_url, review_id, review_board_admin):
    os.chdir(file_path)
    diffs_id_command = '%s%s%s%s%s%s%s'%('curl http://', review_board_url, '/api/review-requests/', str(review_id), '/diffs/ --user ', review_board_admin, ' > diffs_id.json')
    os.system(diffs_id_command)
    diffs_ids = get_diffs_id(file_path)
    for single_id in diffs_ids:
        files_id_command = '%s%s%s%s%s%s%s%s%s%s%s'%('curl http://', review_board_url, '/api/review-requests/', str(review_id), '/diffs/', str(single_id), '/files/ --user ', review_board_admin, ' > files_id_', str(single_id), '.json')
        os.system(files_id_command)

def get_diffs_id(file_path):
    diffs_id_json = open_type_file(file_path, 'diffs_id.json')
    for single_diff_json in diffs_id_json:
        fp_diffs_json = codecs.open(single_diff_json, 'r', 'GBK')
        content_diffs_json = fp_diffs_json.read()
        diffs_id_match = []
        part_split = content_diffs_json.split('http')
        for single_part in part_split:
            diffs_match = re.search(r'diffs\/\d+\/files', single_part)
            if diffs_match is not None:
                diffs_id_match.append(re.search(r'\d+', diffs_match.group()).group())
        diffs_id_list = list(set(diffs_id_match))
        return diffs_id_list
        
def get_files_id(file_path):
    files_id_json = open_type_file(file_path, r'files_id_\d+.json')
    files_id = []
    for single_json in files_id_json:
        fp_files_json = codecs.open(single_json, 'r', 'GBK')
        content_files_json = fp_files_json.read()
        part_match = content_files_json.split('http')
        for single_part in part_match:
            file_id_match = re.search(r'files\/\d+\/patched-file', single_part)
            if file_id_match is not None:
                files_id.append(re.search(r'\d+', file_id_match.group()).group())
    files_id = list(set(files_id))
    return files_id

def get_patched_file_name(file_path):
    patched_file_name = []
    patched_file_name_list = []
    files_id_json = open_type_file(file_path, r'files_id_\d+.json')
    for single_json in files_id_json:
        fp_files_json = codecs.open(single_json, 'r', 'GBK')
        content_files_json =fp_files_json.read()
        part_match = content_files_json.split('http')
        for single_part in part_match:
            name_match = re.findall(r'source_file[\s\S]*dest_file', single_part)
            for single_match in name_match:
                patched_file_name.append(single_match[15:len(single_match)-13])
    for single_patch_name in patched_file_name:
        if single_patch_name[0] == '/':
            patched_file_name_list.append(single_patch_name[1:])
        else:
            patched_file_name_list.append(single_patch_name)
    return patched_file_name_list

# example: 163 email
def send_email(file_path, svn_version_id, review_request_id, flag, email_receivers_success, email_receivers_failure, email_success, email_fail, host_user, host_password, svn_repository_folder):
    subject_success = '%s%s%s%s%s%s'%('CommitCheck: Success, ', svn_repository_folder, ': ', str(svn_version_id), ', review: ', str(review_request_id))
    subject_failure = '%s%s%s%s%s%s%s%s'%('CommitCheck: Fail: ', flag, ', ', svn_repository_folder, ': ',str(svn_version_id), ', review: ', str(review_request_id))
    if flag == 1:
        email_subject = subject_success
        part = MIMEText('Committed the right files !', _subtype='plain')
    elif flag == 2:
        email_subject = subject_failure
        part = MIMEText('More files than review board have been committed, please check the review id !', _subtype='plain')
    elif flag == 3:
        email_subject = subject_failure
        part = MIMEText('Fewer files than review board have been committed !', _subtype='plain')
    elif flag == 0:
        email_subject = subject_failure
        part = MIMEText('The files contents are different from the review board, please check them and the review id !', _subtype='plain')
    else:
        email_subject = subject_failure
        part = MIMEText('No review id !', _subtype='plain')
    mail_host = 'smtp.163.com'
    msg = MIMEMultipart()
    msg['Subject'] = email_subject
    msg['Form'] = host_user
    if flag == 1:
        msg['To'] = email_success[0]
        msg['Cc'] = ', '.join(email_receivers_success)
    else:
        msg['To'] = email_fail[0]
        msg['Cc'] = ', '.join(email_receivers_failure)
    msg.attach(part)
    try:
        part_c = MIMEApplication(open(file_path + 'check.log', 'r').read())
        part_c.add_header('Content-Disposition', 'attachment', filename = 'check.log')
        msg.attach(part_c)
        part_d = MIMEApplication(open(file_path + 'diff.txt', 'r').read())
        part_d.add_header('Content-Disposition', 'attachment', filename = 'diff.txt')
        msg.attach(part_d)
    except:
        pass
    server = smtplib.SMTP()
    server.connect(mail_host)
    server.login(host_user, host_password)
    try:
        if flag == 1:
            server.sendmail(host_user, email_success + email_receivers_success, msg.as_string())
        else:
            server.sendmail(host_user, email_fail + email_receivers_failure, msg.as_string())
        server.close()
        return True
    except:
        return False

def get_email_flag(file_path, changed_files_number, patched_files_number, svn_patch_matched_number):
    if os.path.exists(file_path + 'diff.txt') and os.path.getsize(file_path + 'diff.txt') == 0 and changed_files_number == patched_files_number and svn_patch_matched_number == patched_files_number and svn_patch_matched_number == changed_files_number:
        flag = 1
    elif changed_files_number > patched_files_number or changed_files_number > svn_patch_matched_number:
        flag = 2
    elif changed_files_number < patched_files_number or patched_files_number > svn_patch_matched_number:
        flag = 3
    else:
        flag = 0
    return flag

def get_review_id(file_path, svn_revision_id, svn_repository):
    os.chdir(file_path)
    os.system('svn cleanup')
    svn_log_command = '%s%s%s%s%s'%('svnlook log -r ', str(svn_revision_id), ' ', svn_repository, ' > svn_log_message.txt')
    os.system(svn_log_command)
    open_log_txt = codecs.open(file_path + 'svn_log_message.txt', 'r', 'GBK')
    fp_log = open_log_txt.read()
    fp_log_low = fp_log.lower()
    a = re.search(r'review:\d+', fp_log_low)
    if a is not None:
        review_id = a.group().split(':')[-1]
        return review_id
    else:
        return -1

def get_repository_changed_files_number(file_path, svn_revision_id, svn_repository):
    os.chdir(file_path)
    svn_changed_command = '%s%s%s%s%s'%('svnlook changed -r ', str(svn_revision_id), ' ', svn_repository, '> svn_changed.txt')
    os.system(svn_changed_command)
    open_changed_txt = codecs.open(file_path + 'svn_changed.txt', 'r', 'GBK')
    fp_changed = open_changed_txt.readlines()
    return len(fp_changed)

def get_patched_files_number(file_path):
    patch_path = '%s%s'%(file_path, 'patch_file/')
    patched_file_list = open_all_file(patch_path)
    return len(patched_file_list)

def get_svn_author(file_path, svn_revision_id, svn_repository):
    author_name = []
    look_command = '%s%s%s%s%s'%('svnlook author -r ', str(svn_revision_id), ' ', svn_repository, '> svn_author.txt')
    os.chdir(file_path)
    os.system(look_command)
    open_author_txt = open_type_file(file_path, 'svn_author.txt')
    fp_author_txt = codecs.open(open_author_txt[0], 'r', 'GBK')
    name = fp_author_txt.readline()
    author_name.append(name)
    return author_name

def get_changed_files_list(file_path):
    changed_files = codecs.open(file_path + 'svn_changed.txt', 'r', 'GBK')
    changed_files_list = []
    svn_changed_list = []
    changed_files_name = changed_files.readline()
    while changed_files_name:
        svn_changed_list.append(changed_files_name[3:len(changed_files_name)-1].lstrip())
        changed_files_name = changed_files.readline()
    for single_changed in svn_changed_list:
        if re.search(r'\.', single_changed.split('/')[-1]) is not None:
            changed_files_list.append(single_changed)
    return changed_files_list

def get_changed_path(changed_files_list, svn_repository_folder):
    changed_path_list = []
    for file_name in changed_files_list:
        path_list = file_name.split('/')
        if len(path_list) > 1:
            path = '/'.join(path_list[:-1])
            changed_path_list.append(path)
        else:
            changed_path_list.append(svn_repository_folder)
    changed_path = list(set(changed_path_list))
    return changed_path

# When you commit the code every time, the result folder number will increase.
def get_new_folder_number(file_path):
    if os.path.exists(file_path + 'folder_number.ini'):
        folder_config = ConfigParser.ConfigParser()
        folder_config.readfp(open(file_path + 'folder_number.ini'), 'rb')
        folder_number = folder_config.get('number', 'value')
        new_number = int(folder_number) + 1
        config = ConfigParser.ConfigParser()
        config.add_section('number')
        config.set('number', 'value', new_number)
        with open(file_path + 'folder_number.ini', 'w+') as fc:
            config.write(fc)
        return new_number
    else:
        cfg = ConfigParser.ConfigParser()
        cfg.add_section('number')
        cfg.set('number', 'value', 1)
        with open(file_path + 'folder_number.ini', 'w+') as f:
            cfg.write(f)
        return 1

# Read the parameters from post-commit_cfg.ini.
def read_review_config(file_path):
    if os.path.exists(file_path + 'post-commit_cfg.ini'):
        read_list = []
        config = ConfigParser.ConfigParser()
        config.readfp(open(file_path + 'post-commit_cfg.ini'), 'rb')
        Mail_sender_address = config.get('Mail_sender_address', 'address')
        Mail_sender_password = config.get('Mail_sender_address', 'password')
        Success_receiver_Cc1 = config.get('Success_receiver_Cc', 'address1')
        Success_receiver_Cc2 = config.get('Success_receiver_Cc', 'address2')
        Success_receiver_Cc3 = config.get('Success_receiver_Cc', 'address3')
        Fail_receiver_Cc1 = config.get('Fail_receiver_Cc', 'address1')
        Fail_receiver_Cc2 = config.get('Fail_receiver_Cc', 'address2')
        Fail_receiver_Cc3 = config.get('Fail_receiver_Cc', 'address3')
        Fail_receiver_Cc4 = config.get('Fail_receiver_Cc', 'address4')
        Fail_receiver_Cc5 = config.get('Fail_receiver_Cc', 'address5')
        svn_admin_user = config.get('svn_admin', 'user')
        svn_admin_password = config.get('svn_admin', 'password')
        RB_admin_user = config.get('RB_admin', 'user')
        RB_admin_password = config.get('RB_admin', 'password')
        RB_URL = config.get('RB_URL', 'ip_port')
        work_path = config.get('work_path', 'dir')
        read_list.append(Mail_sender_address.strip())
        read_list.append(Mail_sender_password.strip())
        read_list.append(Success_receiver_Cc1.strip())
        read_list.append(Success_receiver_Cc2.strip())
        read_list.append(Success_receiver_Cc3.strip())
        read_list.append(Fail_receiver_Cc1.strip())
        read_list.append(Fail_receiver_Cc2.strip())
        read_list.append(Fail_receiver_Cc3.strip())
        read_list.append(Fail_receiver_Cc4.strip())
        read_list.append(Fail_receiver_Cc5.strip())
        read_list.append(svn_admin_user.strip())
        read_list.append(svn_admin_password.strip())
        read_list.append(RB_admin_user.strip())
        read_list.append(RB_admin_password.strip())
        read_list.append(RB_URL.strip())
        if work_path[-1] == '/':
            work_path = work_path
        else:
            work_path = work_path + '/'
        read_list.append(work_path)
        return read_list
    else:
        return False

# Print the log for every step.
def _main(svn_revision_id, svn_repository):
    get_abs_path = sys.path[0] + '/'
    config_list = read_review_config(get_abs_path)
    host_user = config_list[0]
    host_password = config_list[1]
    email_success = [config_list[2]]
    email_receiver_success = [config_list[2], config_list[3], config_list[4]]
    email_receiver_failure = [config_list[5], config_list[6], config_list[7], config_list[8], config_list[9]]
    svn_admin = [config_list[10], config_list[11]]
    review_board_admin = '%s%s%s'%(config_list[12], ':', config_list[13])
    review_board_url = config_list[14]
    work_path = config_list[15]
    svn_repository_folder = svn_repository.split('/')[-1]
    folder_number = get_new_folder_number(work_path)
    file_path = '%s%s%s%s'%(work_path, 'files_check_results_', str(folder_number), '/')
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
    os.mkdir(file_path[:-1])
    svn_path = '%s%s%s'%(file_path, 'svn_checkout', '/')
    log_txt = open(file_path + 'check.log', 'w')
    log_txt.write('svn_repository: ')
    log_txt.write('\n\t' + svn_repository + '; ')
    log_txt.write('\nfile_path: ')
    log_txt.write('\n\t' + file_path + '; ')
    changed_files_number = get_repository_changed_files_number(file_path, svn_revision_id, svn_repository)
    log_txt.write('\nchanged_files_number: ')
    log_txt.write(str(changed_files_number) + '; ')
    changed_files_list = get_changed_files_list(file_path)
    log_txt.write('\nchanged_files_number_no_dirs: ')
    log_txt.write(str(len(changed_files_list)) + '; ')
    log_txt.write('\nchanged_files_list: ')
    for cf in changed_files_list:
        log_txt.write('\n\t' + cf + '; ')
    changed_paths_list = get_changed_path(changed_files_list, svn_repository_folder)
    log_txt.write('\nchanged_paths_list: ')
    for cp in changed_paths_list:
        log_txt.write('\n\t' + cp + '; ')
    svn_checkout_pa, svn_up_pa = svn_checkout(svn_path, svn_revision_id, svn_admin, svn_repository, svn_repository_folder, changed_paths_list, changed_files_list)
    log_txt.write('\nsvn_checkout_pa: ')
    log_txt.write(str(svn_checkout_pa) + ';')
    log_txt.write('\nsvn_up_pa: ')
    log_txt.write(str(svn_up_pa) + ';')
    author = get_svn_author(file_path, svn_revision_id, svn_repository)
    log_txt.write('\nauthor: '+ author[0][:-1] + '; ')
	# write your email address
    author_address = 'abc@163.com'   
    email_fail = []
    email_fail.append(author_address)
    review_id = get_review_id(file_path, svn_revision_id, svn_repository)
    log_txt.write('\nreview_id: ')
    log_txt.write(str(review_id) + '; ')
    if review_id == -1:
        log_txt.close()
        send_email(file_path, svn_revision_id, review_id, 4, email_receiver_success, email_receiver_failure, email_success, email_fail, host_user, host_password, svn_repository_folder)
    else:
        try:
            create_information_json(file_path, review_board_url, review_id, review_board_admin)
            diffs_id = get_diffs_id(file_path)
            log_txt.write('\ndiffs_id: ')
            for did in diffs_id:
                log_txt.write(str(did) + '; ')
            patched_file_name = get_patched_file_name(file_path)
            log_txt.write('\npatched_file_name: ')
            for pname in patched_file_name:
                log_txt.write('\n\t' + pname + '; ')
            files_id = get_files_id(file_path)
            log_txt.write('\nfiles_id: ')
            for fid in files_id:
                log_txt.write(str(fid) + '; ')
            patched_api_url = build_patched_file_api_url(review_board_url, review_id, diffs_id, files_id, review_board_admin)
            log_txt.write('\npatched_api_url: ')
            for url in patched_api_url:
                log_txt.write('\n\t' + url.split('--user')[-2] + '; ')
            id_patch_match_list = patched_file_id_match(file_path)
            log_txt.write('\nid_patch_match: ')
            for ipm in id_patch_match_list:
                log_txt.write('\n\t' + ipm + '; ')
            adjust_id_patch_match_list = create_patched_files_dirs(file_path, id_patch_match_list, svn_repository_folder)
            log_txt.write('\nadjust_id_patch_match: ')
            for aipm in adjust_id_patch_match_list:
                log_txt.write('\n\t' + aipm + '; ')
            adjust_dir_name_list, get_patch_file_pa = get_patch_file(file_path, patched_api_url, adjust_id_patch_match_list, svn_repository_folder)
            log_txt.write('\nadjust_dir_name: ')
            for adn in adjust_dir_name_list:
                log_txt.write('\n\t' + adn + '; ')
            log_txt.write('\nget_patch_file_pa: ')
            log_txt.write(str(get_patch_file_pa) + ';')
            svn_patch_matched_number = create_diff_txt(file_path, svn_path, svn_repository_folder)
            log_txt.write('\nsvn_patch_matched_number: ')
            log_txt.write(str(svn_patch_matched_number) + '; ')
            patched_files_number = get_patched_files_number(file_path)
            log_txt.write('\npatched_files_number: ')
            log_txt.write(str(patched_files_number) + '; ')
            flag = get_email_flag(file_path, len(changed_files_list), patched_files_number, svn_patch_matched_number)
            log_txt.write('\nflag: ')
            log_txt.write(str(flag) + '; ')
            svn_co_files = open_none_svn_dir_files(file_path + 'svn_checkout/')
            log_txt.write('\nsvn_co_files: ')
            for scf in svn_co_files:
                log_txt.write('\n\t' + scf + '; ')
            patch_files = open_all_file(file_path + 'patch_file/')
            log_txt.write('\npatched_files: ')
            for pf in patch_files:
                log_txt.write('\n\t' + pf + '; ')
            log_txt.close()
            send_email(file_path, svn_revision_id, review_id, flag, email_receiver_success, email_receiver_failure, email_success, email_fail, host_user, host_password, svn_repository_folder)
        except:
            pass

if __name__ == '__main__':
    svn_repository = sys.argv[1]
    input_revision_id = sys.argv[2]
    _main(input_revision_id, svn_repository)