#!/usr/bin/env python3

import sys
sys.path.append('../')
import configparser
import gi
gi.require_version('Gst', '1.0')

import os
import os.path
from os import path
from distutils.dir_util import copy_tree
from gi.repository import GLib, Gst
from korean_lpr.common.platform_info import PlatformInfo
from korean_lpr.common.bus_call import bus_call
from korean_lpr.lib import pyds

import numpy as np
import csv
import datetime as dt
import geocoder
import cv2
import getpass
import pickle
import requests
import json

from korean_lpr.ui.ui_ui import Ui_MainWindow
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)

from PySide6.QtMultimedia import (QMediaPlayer, QCamera)
from PySide6.QtMultimediaWidgets import (QVideoWidget)
from PySide6.QtWidgets import (QApplication, QCalendarWidget, QCheckBox, QGraphicsView,
    QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMenuBar, QPushButton, QScrollBar, QSizePolicy,
    QStatusBar, QTabWidget, QTableWidget, QTableWidgetItem, QMessageBox,
    QWidget) 
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)

from PIL.ImageQt import ImageQt 
from PIL import Image

recording = False
record_path= None
img_path=''
selected_date=''
selected_drive = ''
pgie_classes_str = ["Vehicle", "TwoWheeler", "Person", "RoadSign"]
plate_number_data = list()
local_data = {"address": None, "auto_send":False, "latest_csv": './korean_lpr/records/start.csv' }
latest_table_items = list()
this_table_items = list()

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3
MUXER_BATCH_TIMEOUT_USEC = 33000

# 모델 변경
SGIE_CLASS_ID_LPD = 0
PRIMARY_DETECTOR_UID = 1
SECONDARY_DETECTOR_UID = 2
SECONDARY_CLASSIFIER_UID = 3
TRACKER_CLASSIFIER_UID = 4

perf_measure = {'pre_time': 0, 'total_time': 0, 'count': 0}
license_plate_record = []
license_plate_coordinate = []
ui = None
internet_connection = False
response = ''
headers = {'Content-Type': 'application/json; charset=utf-8'}

    
print(local_data)
if not path.exists('./korean_lpr/data/local_data.pkl'):
    with open('./korean_lpr/data/local_data.pkl', 'wb') as f:
        pickle.dump(local_data, f)    
else:                                
    with open('./korean_lpr/data/local_data.pkl', 'rb') as f:
        local_data = pickle.load(f)
        if not local_data['latest_csv']:
            local_data['latest_csv'] = './korean_lpr/records/start.csv'
            with open('./korean_lpr/data/local_data.pkl', 'wb') as f:
                pickle.dump(local_data, f)    
                
        if not local_data['address']: 
            local_data['address'] = "https://postman-rest-api-learner.glitch.me/info"
            with open('./korean_lpr/data/local_data.pkl', 'wb') as f:
                pickle.dump(local_data, f)    

def get_latest_table_items():
    global local_data
    global latest_table_items
    with open(os.getcwd()+local_data['latest_csv'][1:], 'rt', encoding='UTF8') as file:
        latest_datalines = csv.reader(file)                                        
        for dataline in latest_datalines:
            latest_table_items.append(dataline)
        print(latest_table_items, "마지막 데이터")    

get_latest_table_items()

print(local_data)

class MainWindow(QMainWindow):
    global change_main_image
    global auto_sending
    global response
    global latest_table_items
    global headers
    global internet_connection
    global ui
    global recording
    global record_path        
    global plate_number_data
    global local_data

    def startRecording(self):
        global record_path        
        global ui
        global recording
        
        print("recording start")
        now = dt.datetime.now()
        images_folder = "./korean_lpr/images/{}".format(now.strftime('%Y-%m-%d'))                                    
        if not path.exists(images_folder):
            os.mkdir(images_folder)
            
        records_folder = "./korean_lpr/records/{}".format(now.strftime('%Y-%m-%d'))                                    
        if not path.exists(records_folder):
            os.mkdir(records_folder)
                                                    
        record_path = "./korean_lpr/records/{}/{}_{}.csv".format(now.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'), now.strftime('%H%M%S'))                                        
        with open(record_path, 'w', newline='') as file:
            writer = csv.writer(file)
            field = ["차량 번호판", "위도","경도","이미지파일", "기록시간", "상태", "시작시간", "출차시간", "주차시간"]
            writer.writerow(field)                                        
        
        # ui.pushButton.setStyleSheet("background-color : red") 
        # ui.pushButton.setText("기록 정지") 
        # ui.pushButton.clicked.connect(self.stopRecording)

        recording = True    
        
        ui.pushButton.setVisible(False)
        ui.pushButton_2.setVisible(True)
        
    def stopRecording(self):
        global record_path        
        global recording
        global plate_number_data
        global ui
        global local_data
        global latest_table_items
        
        print("recording end")
        
        recording = False
        plate_number_data = list()
       
        
        # with open(record_path, 'rt', encoding='UTF8') as file:
            
        
        # with open(record_path, 'w', newline='') as file:
        #     writer = csv.writer(file)
        #     # field = ["차량 번호판", "위도","경도","이미지파일", "기록시간", "상태", "시작시간", "출차시간", "주차시간"]
        #     # writer.writerow(field)
        #     for item in latest_table_items:
        #         if item[0] == label_info.result_label:
        #             parking_state = "주차"
        #             start_time = item[6]    
        #             # parking_time = now - dt.datetime.strptime(item[6], '%Y-%m-%d %H:%M:%S.%f')
        #         else:
        #             parking_state = "주차"
        #             start_time = now
        
        
        #  with open(record_path, 'a') as file:
        #     writer = csv.writer(file)                                                                       

        #     writer.writerow([label_info.result_label, g.lat, g.lng, img_path, now, parking_state, start_time, end_time, parking_time])
        
        local_data['latest_csv'] = record_path
        print(local_data, "로컬데이터")
        with open('./korean_lpr/data/local_data.pkl', 'wb') as f:
                pickle.dump(local_data, f)    
        latest_table_items=list()
        get_latest_table_items()
        
        if local_data['auto_send']:
            self.send_logic()
        ui.tableWidget.setRowCount(0);
        record_path= None
        
        # ui.pushButton.setStyleSheet("background-color : green") 
        # ui.pushButton.setText("기록 시작") 
        ui.pushButton_2.setVisible(False)
        ui.pushButton.setVisible(True)
        
        
    def calendar_change(self):
        global selected_date
        self.ui.listWidget.clear()
        cal_date = ui.calendarWidget.selectedDate()
        selected_date = cal_date.toString('yyyy-MM-dd')  # QDate 를 str 로 변환
        if os.path.exists('./korean_lpr/records/{}'.format(selected_date)):
            record_files = os.listdir('./korean_lpr/records/{}'.format(selected_date))
            self.ui.listWidget.addItems(record_files)
            self.ui.listWidget.sortItems()

    def file_select(self):
        # print("Selected items: ", self.ui.listWidget.selectedItems())
        print("Selected items: ", self.ui.listWidget.selectedItems()[0].text())
        with open('./korean_lpr/records/{}/{}'.format(selected_date, self.ui.listWidget.selectedItems()[0].text()), 'rt', encoding='UTF8') as file:
            tableitems = list()
            datalines = csv.reader(file)
            for dataline in datalines:
                tableitems.append(dataline)
            ui.tableWidget_2.setRowCount(len(tableitems))
            ui.tableWidget_2.setColumnCount(len(tableitems[0]))
            try:
                for row, rowitems in enumerate(tableitems):
                    for col, colitem in enumerate(rowitems):
                        ui.tableWidget_2.setItem(row, col, QTableWidgetItem(rowitems[col]))
            except Exception as e:
                print(e)
            print (ui.tableWidget_2.item(1, 3).text())
            pixmap = QPixmap(ui.tableWidget_2.item(1, 3).text())
            pixmap.scaled(100, 405, Qt.KeepAspectRatio)
            ui.label_9.setPixmap(pixmap) 
            ui.label_9.setScaledContents(True)
    
    def record_select(self):
        selected_row = ui.tableWidget_2.currentRow()
        if selected_row>0:
            pixmap = QPixmap(ui.tableWidget_2.item(selected_row, 3).text())
            pixmap.scaled(100, 405, Qt.KeepAspectRatio)
            ui.label_9.setPixmap(pixmap) 
            ui.label_9.setScaledContents(True)
            
    def usb_file_copy(self):
        global selected_drive
        drives = os.listdir('/media/{}'.format(getpass.getuser()))
        for drive in drives:
            if not drive == 'L4T-README':        
                selected_drive = drive
        
        print(selected_drive)
        from_file_path = os.getcwd()+'/korean_lpr/records' # 복사할 파일
        to_file_path = '/media/{}/{}'.format(getpass.getuser(), selected_drive)+'/korean_lpr/records' # 복사될 파일
        copy_tree(from_file_path, to_file_path) 
        QMessageBox.information(self, "USB 복사", "USB에 파일이 복사되었습니다.")  
        # records_folders = os.listdir('./korean_lpr/records')
        # if not path.exists(records_folder):
        #     os.mkdir(records_folder)

    def push_change_sending_status_button(self):
            
        if local_data['auto_send']:
            ui.pushButton_6.setVisible(True)
            ui.pushButton_7.setVisible(False)
            local_data['auto_send'] = False       
        else:
            ui.pushButton_6.setVisible(False)
            ui.pushButton_7.setVisible(True)
            local_data['auto_send'] = True
        with open('./korean_lpr/data/local_data.pkl', 'wb') as f:
            pickle.dump(local_data, f)   
        
    def exit_program(self):
        sys.exit(main(sys.argv))    
        
    def send_data(self):        
        self.send_logic()
        self.send_message_popup()
        
    def send_logic(self):    
        global local_data
        global response
        # global internet_connection
        
        local_data['address'] = ui.lineEdit.text()
        with open('./korean_lpr/data/local_data.pkl', 'wb') as f:
            pickle.dump(local_data, f)   

        try:
            response = requests.post( local_data['address'], headers=headers, data=json.dumps(latest_table_items))
            # internet_connection = True       
            ui.plainTextEdit.setPlainText(response.text)   
            print("response.text: ", response.text)
        except requests.ConnectionError:
            QMessageBox.information(self, "자동전송실패", "인터넷이 연결되어있지 않아 자동전송에 실패하였습니다.이 메시지를 보고 싶지 않을경우 설정에서 자동전송을 꺼주세요.")  
            # internet_connection = False

    def send_message_popup(self):    
        QMessageBox.information(self, "데이터전송", "서버에 데이터 전송이 완료되었습니다.")      

    def __init__(self):
        global selected_drive
        global img_path
        global local_data
        global response
        super(MainWindow, self).__init__()
        records_folders = os.listdir('./korean_lpr/records')
        global ui
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        ui = self.ui
        
        drives = os.listdir('/media/{}'.format(getpass.getuser()))
        for drive in drives:
            if not drive == 'L4T-README':        
                selected_drive = drive
        if (selected_drive):
            self.ui.lineEdit_2.setText(selected_drive)
        self.ui.lineEdit.setText(local_data['address'])   
        self.ui.pushButton.clicked.connect(self.startRecording)
        self.ui.pushButton.setStyleSheet("background-color : green") 
        self.ui.pushButton_2.clicked.connect(self.stopRecording)
        self.ui.pushButton_2.setStyleSheet("background-color : red") 
        self.ui.pushButton_2.setVisible(False)
        
        self.ui.pushButton_3.clicked.connect(self.usb_file_copy)
        self.ui.pushButton_4.setStyleSheet("background-color : red")
        self.ui.pushButton_4.clicked.connect(self.exit_program)
        self.ui.pushButton_5.clicked.connect(self.send_data)
        
        self.ui.pushButton_6.clicked.connect(self.push_change_sending_status_button)
        self.ui.pushButton_6.setStyleSheet("background-color : green")
        self.ui.pushButton_7.clicked.connect(self.push_change_sending_status_button)
        self.ui.pushButton_7.setStyleSheet("background-color : red")
        
        
            
        
        self.ui.calendarWidget.setGridVisible(True)
        self.ui.calendarWidget.selectionChanged.connect(self.calendar_change)

        self.ui.listWidget.itemSelectionChanged.connect(self.file_select)
        self.ui.tableWidget_2.itemSelectionChanged.connect(self.record_select)
        self.ui.tabWidget.setCurrentIndex(0)
        # self.ui.listWidget.itemActivated.connect(self.file_select)
        # self.ui.tableWidget_2.setRowCount(len(tableitems))
        # self.ui.tableWidget_2.setColumnCount(len(tableitems[0]))
        # try:
        #     for row, rowitems in enumerate(tableitems):
        #         for col, colitem in enumerate(rowitems):
        #             self.ui.tableWidget_2.setItem(row, col, QTableWidgetItem(rowitems[col]))
        # except Exception as e:
        #     print(e)    
            
def osd_sink_pad_buffer_probe(pad,info,u_data):
    global recording
    global record_path
    global img_path
    global ui
    
    frame_number=0
    
    obj_counter = {
        PGIE_CLASS_ID_VEHICLE:0,
        PGIE_CLASS_ID_PERSON:0,
        PGIE_CLASS_ID_BICYCLE:0,
        PGIE_CLASS_ID_ROADSIGN:0
    }
    num_rects=0

    # 모델 변경
    vehicle_count = 0
    person_count = 0
    lp_count = 0
    frame_count[0] += 1
    
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # Retrieve batch metadata from the gst_buffer
    # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
    # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting is done by pyds.NvDsFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            
            
        except StopIteration:
            break

        frame_number=frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj=frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            
            # 모델 변경
            
            #Check that the object has been detected by the primary detector
            #and that the class id is that of vehicles/persons.
            if(obj_meta.unique_component_id == PRIMARY_DETECTOR_UID):
                # print("primary_detector is working")
                # print("vehicle_tracking_id: " + str(obj_meta.object_id))
                if(obj_meta.class_id == PGIE_CLASS_ID_VEHICLE):
                    vehicle_count += 1
                if(obj_meta.class_id == PGIE_CLASS_ID_PERSON):
                    person_count += 1

            # if(obj_meta.unique_component_id == SECONDARY_DETECTOR_UID):
            #     # print("secondary_detector is working")
            #     parent_obj_meta = pyds.NvDsObjectMeta.cast(obj_meta.parent)
            #     parent_tracking_id = str(parent_obj_meta.object_id)
            #     # print("parent_tracking_id: " + parent_tracking_id)
            #     if(obj_meta.class_id == SGIE_CLASS_ID_LPD):
            #         lp_count += 1
            #     #print(obj_meta.rect_params)
            #     rect_params_info = obj_meta.rect_params
            #     # print("rect_params_left: " + str(rect_params_info.left))
            #     # print("rect_params_top: " + str(rect_params_info.top))
            #     # print("rect_params_width: " + str(rect_params_info.width))
            #     # print("rect_params_height: " + str(rect_params_info.height))
            #     # print("trackingId: " + str(parent_tracking_id))
            #     # print("frame: " + str(frame_count[0]))
            #     license_plate_coordinate.append([frame_count[0], parent_tracking_id, rect_params_info.left, rect_params_info.top, rect_params_info.width, rect_params_info.height])


            l_class = obj_meta.classifier_meta_list  
            while l_class is not None:
                try:
                    class_meta = pyds.NvDsClassifierMeta.cast(l_class.data)
                except StopIteration:
                    break
                if(not class_meta):
                    continue

                if(class_meta.unique_component_id == SECONDARY_CLASSIFIER_UID):
                    # print("secondary_classifier is working")
                    label_i = 0
                    l_label = class_meta.label_info_list
                    while(label_i < class_meta.num_labels and l_label):

                        label_info = pyds.NvDsLabelInfo.cast(l_label.data)
                        if(label_info):
                            if(label_info.label_id == 0 and label_info.result_class_id == 1):
                                result_label = label_info.result_label
                                if(len(license_plate_record)>5):
                                    if not result_label in license_plate_record[-5:]:
                                        license_plate_record.append(result_label)
                                else:
                                    if not result_label in license_plate_record:
                                        license_plate_record.append(result_label)

                                # print("-Plate License: " + label_info.result_label)
                                
                                if recording :
                                                                                                    
                                    if label_info.result_label not in plate_number_data:                              
                                        plate_number_data.append(label_info.result_label)
                                        print(plate_number_data)
                                        print(label_info.result_label + " is not in the list")
                                        
                                        def recording_function():
                                            global record_path
                                            global this_table_items
                                            now = dt.datetime.now()
                                            g = geocoder.ip('me')
                                            
                                            img_path = "./korean_lpr/images/{}/{}_{}_{}.jpg".format(now.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), frame_number)
                                            
                                            n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                                            # convert python array into numpy array format in the copy mode.
                                            frame_copy = np.array(n_frame, copy=True, order='C')
                                            #covert the array into cv2 default color format
                                            frame_image=cv2.cvtColor(frame_copy, cv2.COLOR_RGBA2BGRA)                                    
                                            cv2.imwrite(img_path, frame_image)
                                            
                                            pixmap = QPixmap(img_path)
                                            pixmap.scaled(100, 405, Qt.KeepAspectRatio)
                                            ui.label_8.setPixmap(pixmap) 
                                            ui.label_8.setScaledContents(True)
                                                                                                                                                                                
                                            parking_state = ""
                                            start_time = None
                                            end_time = None
                                            parking_time = None
        
                                                # ui.tableWidget.setRowCount(len(tableitems))
                                                # ui.tableWidget.setColumnCount(len(tableitems[0]))
                                                # try:
                                                #     for row, rowitems in enumerate(tableitems):
                                                #         for col, colitem in enumerate(rowitems):
                                                #             ui.tableWidget.setItem(row, col, QTableWidgetItem(rowitems[col]))
                                                # except Exception as e:
                                                #     print(e)
                                            
                                            with open(record_path, 'a') as file:
                                                writer = csv.writer(file)                                                                       
                                                for item in latest_table_items:
                                                    if item[0] == label_info.result_label:
                                                        parking_state = "주차"
                                                        start_time = item[6]    
                                                        # parking_time = now - dt.datetime.strptime(item[6], '%Y-%m-%d %H:%M:%S.%f')
                                                    else:
                                                        parking_state = "주차"
                                                        start_time = now

                                                writer.writerow([label_info.result_label, g.lat, g.lng, img_path, now, parking_state, start_time, end_time, parking_time])
                                            
                                            with open(record_path, 'rt', encoding='UTF8') as file:
                                                this_table_items=list()
                                                datalines = csv.reader(file)
                                                for dataline in datalines:
                                                    this_table_items.append(dataline)
                                                ui.tableWidget.setRowCount(len(this_table_items))
                                                ui.tableWidget.setColumnCount(len(this_table_items[0]))
                                                try:
                                                    for row, rowitems in enumerate(this_table_items):
                                                        for col, colitem in enumerate(rowitems):
                                                            ui.tableWidget.setItem(row, col, QTableWidgetItem(rowitems[col]))
                                                            
                                                            if rowitems[col] == "주차":
                                                                ui.tableWidget.item(row, col).setBackground(QColor(100,100,200))
                                                            elif rowitems[col] == "출차":
                                                                ui.tableWidget.item(row, col).setBackground(QColor(200,100,100))
                                                            
                                                except Exception as e:
                                                    print(e)
                                                
                                        if label_info.result_label[0].isdigit():
                                            # print (label_info.result_label[1])
                                            # print("숫자로 시작")
                                            if 6 < len(label_info.result_label) <9:
                                                # print(len(label_info.result_label))
                                                # print("글자갯수 7-8범위 내")
                                                if label_info.result_label[0:3].isdigit():                                                                                                    
                                                    # print(label_info.result_label[0:3])
                                                    # print("앞3자리 숫자")
                                                    if not label_info.result_label[3].isdigit():                                                                                                    
                                                        # print("4번째 자리 한글")
                                                        # print(label_info.result_label[4:])
                                                        if len(label_info.result_label[4:]) == 4:
                                                            recording_function()
                                                else:
                                                    # print("앞2자리 숫자")                                                    
                                                    if not label_info.result_label[2].isdigit():                                                                                                    
                                                        # print("3번째 자리 한글")
                                                        # print(label_info.result_label[3:])
                                                        if len(label_info.result_label[3:]) == 4:
                                                            recording_function()                                    
                                        else:
                                            print("글자로 시작")
                                            local_name = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
                                            if label_info.result_label[0:2] in local_name:
                                                print("지역명으로 시작")
                                                if 7 <len(label_info.result_label) <10:
                                                    print("글자갯수 8-9범위 내")
                                                    if label_info.result_label[2:4].isdigit():                                                
                                                        print("3-4자리 숫자")
                                                    if not label_info.result_label[4].isdigit():                                                                                                    
                                                        print("5번째 자리 한글")
                                                        recording_function()
                                                
                        label_i += 1
                        l_label = l_label.next
                   
                try:
                    l_class = l_class.next
                except StopIteration:
                    break
 
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break
        # Acquiring a display meta object. The memory ownership remains in
        # the C code so downstream plugins can still access it. Otherwise
        # the garbage collector will claim it when this probe function exits.
        display_meta=pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
        # Setting display text to be shown on screen
        # Note that the pyds module allocates a buffer for the string, and the
        # memory will not be claimed by the garbage collector.
        # Reading the display_text field here will return the C address of the
        # allocated string. Use pyds.get_string() to get the string content.
        # 프레임 표시
        py_nvosd_text_params.display_text = "Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}".format(frame_number, num_rects, obj_counter[PGIE_CLASS_ID_VEHICLE], obj_counter[PGIE_CLASS_ID_PERSON])

        # Now set the offsets where the string should appear
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12

        # Font , font-color and font-size
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        # set(red, green, blue, alpha); set to White
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

        # Text background color
        py_nvosd_text_params.set_bg_clr = 1
        # set(red, green, blue, alpha); set to Black
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        # Using pyds.get_string() to get display_text as string
        
        # print(pyds.get_string(py_nvosd_text_params.display_text))
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
        
        n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
        frame_copy = np.array(n_frame, copy=True, order='C')
        
        frame_image=cv2.cvtColor(frame_copy, cv2.COLOR_RGBA2BGRA)
        PIL_image = Image.fromarray(frame_image).convert('RGB')
        pixmap = QPixmap.fromImage(ImageQt(PIL_image))                                    
        pixmap.scaled(100, 405, Qt.KeepAspectRatio)
        ui.label_10.setPixmap(pixmap) 
        ui.label_10.setScaledContents(True)
        
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
    
    frame_number = frame_meta.frame_num
    #past tracking meta data
    l_user=batch_meta.batch_user_meta_list
    while l_user is not None:
        try:
            # Note that l_user.data needs a cast to pyds.NvDsUserMeta
            # The casting is done by pyds.NvDsUserMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone
            user_meta=pyds.NvDsUserMeta.cast(l_user.data)
        except StopIteration:
            break
        if(user_meta and user_meta.base_meta.meta_type==pyds.NvDsMetaType.NVDS_TRACKER_PAST_FRAME_META):
            try:
                # Note that user_meta.user_meta_data needs a cast to pyds.NvDsTargetMiscDataBatch
                # The casting is done by pyds.NvDsTargetMiscDataBatch.cast()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone
                pPastDataBatch = pyds.NvDsTargetMiscDataBatch.cast(user_meta.user_meta_data)
    
            except StopIteration:
                break
            
            
                # for miscDataStream in pyds.NvDsTargetMiscDataBatch.list(pPastDataBatch):                    
                #     print("streamId=",miscDataStream.streamID)
                #     print("surfaceStreamID=",miscDataStream.surfaceStreamID)
                #     for miscDataObj in pyds.NvDsTargetMiscDataStream.list(miscDataStream):
                #         print("numobj=",miscDataObj.numObj)
                #         print("uniqueId=",miscDataObj.uniqueId)
                #         print("classId=",miscDataObj.classId)
                #         print("objLabel=",miscDataObj.objLabel)
                    #     for miscDataFrame in pyds.NvDsTargetMiscDataObject.list(miscDataObj):
                    #         print('frameNum:', miscDataFrame.frameNum)
                    #         print('tBbox.left:', miscDataFrame.tBbox.left)
                    #         print('tBbox.width:', miscDataFrame.tBbox.width)
                    #         print('tBbox.top:', miscDataFrame.tBbox.top)
                    #         print('tBbox.right:', miscDataFrame.tBbox.height)
                #             print('confidence:', miscDataFrame.confidence)
                #             print('age:', miscDataFrame.age)
            
            
                # masks = pyds.get_segmentation_masks(pPastDataBatch)
                # masks = np.array(masks, copy=True, order='C')
                
                # frame_image = map_mask_as_display_bgr(masks)
                # cv2.imwrite(folder_name + "/" + str(frame_number) + ".jpg", frame_image)    
            
        try:
            l_user=l_user.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK	

    print("Vehicle Count = {0} Person Count = {1} License Plate Count = {2}"
        .format(vehicle_count, person_count, lp_count))
    return Gst.PadProbeReturn.OK

def map_mask_as_display_bgr(mask):
    """ Assigning multiple colors as image output using the information
        contained in mask. (BGR is opencv standard.)
    """
    # getting a list of available classes
    m_list = list(set(mask.flatten()))

    shp = mask.shape
    bgr = np.zeros((shp[0], shp[1], 3))
    for idx in m_list:
        bgr[mask == idx] = [128, 128, 64]
    return bgr

def bus_call(bus, message, loop):
    t = message.type
    if t == Gst.MessageType.EOS:
        print("End of Stream")
        loop.quit()
    elif t == Gst.MessageType.WARNING:
        error, debug = message.parse_warning()
        sys.stderr.write("Warning: %s: %s" % (error, debug))
    elif t == Gst.MessageType.ERROR:
        error, debug = message.parse_error()
        sys.stderr.write("Error: %s: %s" % (error, debug))
        loop.quit()

def cb_new_pad(demuxer, pad, src_ele):
    if pad.get_property("template").name_template == "video_%u":
        src_ele_pad = src_ele.get_static_pad("sink")
        pad.link(src_ele_pad)

def set_tracker_properties(nvtracker, config_file_name):
    print("Setting tracker")
    config = configparser.ConfigParser()
    config.read(config_file_name)

    #print(config.sections())
    section = config.sections()
    #print(section[0])
    for k, v in config[section[0]].items():
        #print("{0}={1}".format(k, v))
        if(k == 'tracker-width'):
            nvtracker.set_property(k, int(v))
        elif(k == 'tracker-height'):
            nvtracker.set_property(k, int(v))
        elif(k == 'gpu-id'):
            nvtracker.set_property(k, int(v))
        elif(k == 'll-lib-file'):
            nvtracker.set_property(k, v)
        elif(k == 'll-config-file'):
            nvtracker.set_property(k, v)
        # elif(k == 'enable-batch-process'):
        #     nvtracker.set_property(k, int(v))
    return True

def main(args):
    # Check input arguments
    # if(len(args)<2):
    #     sys.stderr.write("usage: %s <h264_elementary_stream>\n" % args[0])
    #     sys.exit(1)

    platform_info = PlatformInfo()
    # Standard GStreamer initialization
    Gst.init(None)

    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    # Source element for reading from the file
    print("Creating Source \n ")
    # source = Gst.ElementFactory.make("v4l2src", "usb-cam-source")
    source = Gst.ElementFactory.make("v4l2src", "usb-cam-source")
    if not source:
        sys.stderr.write(" Unable to create Source \n")

    caps_v4l2src = Gst.ElementFactory.make("capsfilter", "v4l2src_caps")
    if not caps_v4l2src:
        sys.stderr.write(" Unable to create v4l2src capsfilter \n")

    print("Creating Video Converter \n")

    # videoconvert to make sure a superset of raw formats are supported
    vidconvsrc = Gst.ElementFactory.make("videoconvert", "convertor_src1")
    if not vidconvsrc:
        sys.stderr.write(" Unable to create videoconvert \n")
    # nvvideoconvert to convert incoming raw buffers to NVMM Mem (NvBufSurface API)
    nvvidconvsrc = Gst.ElementFactory.make("nvvideoconvert", "convertor_src2")
    if not nvvidconvsrc:
        sys.stderr.write(" Unable to create Nvvideoconvert \n")

    caps_vidconvsrc = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    if not caps_vidconvsrc:
        sys.stderr.write(" Unable to create capsfilter \n")
    # Create nvstreammux instance to form batches from one or more sources.
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create NvStreamMux \n")

    # Use nvinfer to run inferencing on decoder's output,
    # behaviour of inferencing is set through config file
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write(" Unable to create pgie \n")

    sgie1 = Gst.ElementFactory.make("nvinfer", "secondary1-nvinference-engine")
    if not sgie1:
        sys.stderr.write(" Unable to make sgie1 \n")

    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    if not tracker:
        sys.stderr.write(" Unable to create tracker \n")


    sgie2 = Gst.ElementFactory.make("nvinfer", "secondary2-nvinference-engine")
    if not sgie2:
        sys.stderr.write(" Unable to make sgie2 \n")

    # Add nvvidconv1 and filter1 to convert the frames to RGBA
    # which is easier to work with in Python.
    print("Creating nvvidconv1 \n ")
    nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
    if not nvvidconv1:
        sys.stderr.write(" Unable to create nvvidconv1 \n")
    print("Creating filter1 \n ")
    caps1 = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA")
    filter1 = Gst.ElementFactory.make("capsfilter", "filter1")
    if not filter1:
        sys.stderr.write(" Unable to get the caps filter1 \n")
    filter1.set_property("caps", caps1)


    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvidconv \n")

    # Create OSD to draw on the converted RGBA buffer
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")

    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")

    # Finally render the osd output
    if platform_info.is_integrated_gpu():
        print("Creating nv3dsink \n")
        # 화면에 보이게 만드는 부분
        sink = Gst.ElementFactory.make("nv3dsink", "nv3d-sink")
        if not sink:
            sys.stderr.write(" Unable to create nv3dsink \n")
    else:
        if platform_info.is_platform_aarch64():
            print("Creating nv3dsink \n")
            # 화면에 보이게 만드는 부분
            sink = Gst.ElementFactory.make("nv3dsink", "nv3d-sink")
            
        else:
            print("Creating EGLSink \n")
            sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
        if not sink:
            sys.stderr.write(" Unable to create egl sink \n")

    # print("Playing cam %s " %args[1])
    caps_v4l2src.set_property('caps', Gst.Caps.from_string("video/x-raw, framerate=30/1"))
    caps_vidconvsrc.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
    # source.set_property('device', args[1])
    source.set_property('device', '/dev/video0')
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)

    print("Setting primary detector")
    pgie.set_property('config-file-path', './korean_lpr/config/pgie_config.txt')
    pgie.set_property('unique-id', PRIMARY_DETECTOR_UID)

    print("Setting secondary detector")
    sgie1.set_property('config-file-path', './korean_lpr/config/sgie1_config.txt')
    sgie1.set_property('unique-id', SECONDARY_DETECTOR_UID)
    sgie1.set_property('process-mode', 2)

    print("Setting secondary classifier")
    sgie2.set_property('config-file-path', './korean_lpr/config/sgie2_config.txt')
    sgie2.set_property('unique-id', SECONDARY_CLASSIFIER_UID)
    sgie2.set_property('process-mode', 2)
    
    name = './korean_lpr/config/tracker_config.txt'
    if(not set_tracker_properties(tracker, name)):
        print("Failed to set tracker1 properties. Exiting.")
        return -1

    # Set sync = false to avoid late frame drops at the display-sink
    sink.set_property('sync', False)

    queue1=Gst.ElementFactory.make("queue","queue1")
    queue2=Gst.ElementFactory.make("queue","queue2")
    queue3=Gst.ElementFactory.make("queue","queue3")
    queue4=Gst.ElementFactory.make("queue","queue4")
    queue5=Gst.ElementFactory.make("queue","queue5")

    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue3)
    pipeline.add(queue4)
    pipeline.add(queue5)

    print("Adding elements to Pipeline \n")
    pipeline.add(source)
    pipeline.add(caps_v4l2src)
    pipeline.add(vidconvsrc)
    pipeline.add(nvvidconvsrc)
    pipeline.add(caps_vidconvsrc)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(sgie1)
    pipeline.add(tracker)
    pipeline.add(sgie2)
    pipeline.add(filter1)
    pipeline.add(nvvidconv1)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)
    
    print("Linking elements in the Pipeline \n")
    source.link(caps_v4l2src)
    caps_v4l2src.link(vidconvsrc)
    vidconvsrc.link(nvvidconvsrc)
    nvvidconvsrc.link(caps_vidconvsrc)
    sinkpad = streammux.request_pad_simple("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
        
     #USB Camera 
    srcpad = caps_vidconvsrc.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of decoder \n")
    srcpad.link(sinkpad)
    streammux.link(queue1)
    queue1.link(pgie)
    pgie.link(queue2)
    queue2.link(sgie1)
    sgie1.link(queue3)
    queue3.link(tracker)
    tracker.link(queue4)   
    queue4.link(sgie2)
    sgie2.link(queue5)
    queue5.link(nvvidconv1)
    nvvidconv1.link(filter1)
    filter1.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(sink)


    # create and event loop and feed gstreamer bus mesages to it
    loop = GLib.MainLoop()

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.
    osdsinkpad = nvosd.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")
    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    print("Starting pipeline \n")
    
    # start play back and listed to events
    pipeline.set_state(Gst.State.PLAYING)
    try:
      loop.run()
    except:
      pass

    # cleanup
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    frame_count = [0]

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    sys.exit(main(sys.argv))

