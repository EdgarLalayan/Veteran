
import fitz
import base64
import argparse
import json
import re
import io
import os
import subprocess
from tqdm import tqdm
import shutil

#import ocrmypdf
import requests

class PDFParser:
    def __init__(self,path=''):
        if path:
            data = self.get_text(path)
            rating_get_res = self._rating_get(data)
            active_get_res = self._active_get(data)
            subject_get_res = self._subject_get(data)
            no_compes_get_res = self._noCompesation(data)
            get_deferredIssues = self._get_deferredIssues(data)
            get_Decision = self._get_Decision(data)
            self._create_data_for_json(rating_get_res,active_get_res,subject_get_res,no_compes_get_res,get_deferredIssues,get_Decision)
            with open('file.json', 'r') as f:
                d  = json.load(f)
                #pretty-print the JSON data
                print(json.dumps(d, indent=2))


    def process_pdf_files(self):
        current_dir = os.getcwd()
        pdf_files = [file for file in os.listdir(current_dir) if file.endswith(".pdf")]
        for pdf_file in tqdm(pdf_files):
            pdf_folder = pdf_file.split('.')[0]
            os.makedirs(pdf_folder, exist_ok=True)
            command = ["python3", "pdfParser.py", "--argument", pdf_file]
            subprocess.run(command, cwd=current_dir)
            pdf_file_copy_path = os.path.join(pdf_folder, pdf_file)
            shutil.copy(os.path.join(current_dir, pdf_file), pdf_file_copy_path)
            json_file = "file.json"
            json_file_copy_path = os.path.join(pdf_folder, f"{os.path.splitext(pdf_file)[0]}.json")
            shutil.move(os.path.join(current_dir, json_file), json_file_copy_path)

    def text_file(self,pdf):
        b64 = self._pdf_to_b64(pdf)
        with open(f'{pdf[:-3]}txt', 'w') as file:
            file.write(b64)

    def get_text(self,pdf):
        text = self._pdf_to_text(pdf)
        return text
    
    def _pdf_to_b64(self,pdf_path):
        with open(pdf_path, "rb") as pdf_file:
            pdf_data = pdf_file.read()

        pdf_b64_string = base64.b64encode(pdf_data).decode("utf-8")

        return pdf_b64_string

    def _pdf_to_text(self,pdf_path):
        if pdf_path.endswith('.txt'):
            with open(pdf_path, 'r') as f:
                b64_string = f.read()
        elif pdf_path.startswith('http'):
            response = requests.get(pdf_path)
            pdf_as_binary_string = response.content
            b64_string = base64.b64encode(pdf_as_binary_string).decode('utf-8')
        else:
            b64_string = self._pdf_to_b64(pdf_path)

        pdf_as_binary_string = base64.b64decode(b64_string)
        binary_stream = io.BytesIO(pdf_as_binary_string)
        datas = []
        pdf_file = fitz.open(stream=binary_stream, filetype='pdf')
        for page_num in range(pdf_file.page_count):
            page = pdf_file[page_num]
            page_text = page.get_text()
            data = page_text.replace('\n', '|')
            if '�' in data:
                data = data.replace("�", " ")
            datas.append(data)

        return datas

    #RATING GET
    def _rating_get(self,data,text=False):
        data = ''.join(data).replace('\n','|')

        lst = data.split('|')

        activeDutydict = {
            'Veterane_name':'None',
            'Va_File_Number':'None',
            'SOCIAL SECURITY NR':'None',
            'POA':'None',
            'CLIENT_CASPIO_FK':'',
            'HEADER_DATE':''
            }
        
        lst  = [i for i in lst if i]
        if 'Rating Decision' not in lst:
            if 'COPY TO' not in  lst[-1] and '/'  in lst[-1]:   
                CLIENT_CASPIO_FK = lst[-2]
                activeDutydict['CLIENT_CASPIO_FK'] = CLIENT_CASPIO_FK
                activeDutydict['HEADER_DATE'] = lst[-1]
            if 'COPY TO' not in  lst[-1] and '/' not in lst[-1]:   
                CLIENT_CASPIO_FK = lst[-1]
                activeDutydict['CLIENT_CASPIO_FK'] = CLIENT_CASPIO_FK
                if '/' in lst[-2]:
                    activeDutydict['HEADER_DATE'] = lst[-2]
 
            



        if 'Rating Decision'  in lst:
            #get CLIENT_CASPIO_FK
            if 'COPY TO' not in  lst[-1] and '/' not in lst[-1]:   
                CLIENT_CASPIO_FK = lst[-1]
                activeDutydict['CLIENT_CASPIO_FK'] = lst[-1]
            if 'COPY TO' not in  lst[-1] and '/'  in lst[-1]:   
                CLIENT_CASPIO_FK = lst[-2]
                activeDutydict['CLIENT_CASPIO_FK'] = CLIENT_CASPIO_FK
                activeDutydict['HEADER_DATE'] = lst[-1]
            #get HEADER DATE
            for i in lst:
                if 'Page' in i :
                    h = lst.index(i)
                    h = lst[h+1]
                    if h[0].isnumeric() and '/' in h:
                        activeDutydict['HEADER_DATE'] = h.strip()
        #remove ccfk 
        lst = [i for i in lst if CLIENT_CASPIO_FK not in i]
        if text== True:
            return lst
        while True:
            try :
                if len(lst) ==0:
                    break
                #VETERANE NAME
                if 'NAME OF VETERAN' in lst[0] and 'VA FILE NUMBER' not in lst[1]:
                    activeDutydict['Veterane_name'] = lst[1].rstrip()
                    if 'VA FILE NUMBER' not in lst[2]:
                        activeDutydict['Veterane_name'] = activeDutydict['Veterane_name']+' '+lst[2].rstrip()
                    del lst[0]
                    continue
                #VA NUMBER
                if 'VA FILE NUMBER' in lst[0] and 'SOCIAL SECURITY NR' not in lst[1]:
                    activeDutydict['Va_File_Number'] = lst[1]
                    del lst[0]
                    continue
                #SOCIAL NUMBER
                if 'SOCIAL SECURITY NR' in lst[0] and 'POA' not in lst[1]:
                    activeDutydict['SOCIAL SECURITY NR'] = lst[1]
                    del lst[0]
                    continue
                #POA
                if 'POA' in lst[0] and 'COPY TO' not in lst[1] and '/' not in lst[1]:
                    activeDutydict['POA'] = lst[1].rstrip()
                    if 'COPY TO' not in lst[2] and '/' not in lst[2] :
                        activeDutydict['POA'] = activeDutydict['POA'] + ' ' + lst[2].rstrip()
                    if 'COPY TO' not in lst[3] and '/' not in lst[3]:
                        activeDutydict['POA'] = activeDutydict['POA'] + ' ' + lst[3].rstrip()
                
                del lst[0]
            except IndexError:
                break

        return activeDutydict  

    #ACTIVE GET
    def _active_get(self,data,text=False):
        data = ''.join(data).replace('\n','|')
        lst = data.split('|')
        activeDutydict = {
            'EOD_Date':'None',
            'RAD_Date':'None',
            'Branch_Service':'None',
            'Discharge_Type':'None',
            }
        info_dics = []
        checker = False
        for row in lst:
            if row.strip() == '':
                del lst[lst.index(row)]
            if 'CHARACTER OF' in row or 'CHARACTEROF' in row:
                lst = lst[lst.index(row):]
                checker = True
        if checker == False:
            return 'None'
        
        pattern_date = r'\d{2}/\d{2}/\d{4}'
        if text == True:
            return lst
        while True:

            if 'LEGACY CODES' in lst[1] or 'LEGACYCODES' in lst[1] :
                break
            
            if  '/' not in lst[1] and ('/'and'LEGACY')  not in lst[2]:
                activeDutydict['EOD_Date'] = ' '
                activeDutydict['RAD_Date'] = ' '
                activeDutydict['Branch_Service'] = lst[1]
                activeDutydict['Discharge_Type'] = lst[2]
                del lst[1]
                del lst[1]
                info_dics.append(activeDutydict.copy())
                activeDutydict['EOD_Date'] = 'None'
                activeDutydict['RAD_Date'] = 'None'
                activeDutydict['Branch_Service']= 'None'
                activeDutydict['Discharge_Type']= 'None'
                continue
            if  len(lst[1].split()) == 1 and '/' in lst[1] and '/' in lst[2] and len(lst[2].split()) == 1:
                activeDutydict['EOD_Date'] = lst[1]
                activeDutydict['RAD_Date'] = lst[2]
                #BRANCH 2x
                if (lst[5][:2].isnumeric() ==False)  and 'LEGACY CODES' not in lst[5]:
                    activeDutydict['Branch_Service'] = lst[3]+' '+lst[4]
                    del lst[4]
                    #BRANCH 3x
                    if (lst[5][:2].isnumeric() ==False)  and 'LEGACY CODES' not in lst[5]:
                        activeDutydict['Branch_Service'] = activeDutydict['Branch_Service']+' '+lst[4]
                        del lst[4]

                #BRANCH 1x
                else:
                    activeDutydict['Branch_Service'] = lst[3]
                
                activeDutydict['Discharge_Type'] = lst[4]
                del lst[1]
                del lst[1]
                del lst[1]
                del lst[1]
                info_dics.append(activeDutydict.copy())
                activeDutydict['EOD_Date'] = 'None'
                activeDutydict['RAD_Date'] = 'None'
                activeDutydict['Branch_Service'] = 'None'
                activeDutydict['Discharge_Type'] = 'None' 
                continue     

            #broken pdfs                                       
            if  len(lst[1].split()) > 1 or len(lst[2].split()) > 1:

                s = lst[1].split()
                
                if  (re.search(pattern_date, lst[2]) and len(lst[2].split()) > 1) and  (re.search(pattern_date, lst[1]) and len(lst[1].split()) == 1):
                    activeDutydict['EOD_Date'] = lst[1].strip()
                    activeDutydict['RAD_Date'] = re.search(pattern_date, lst[2]).group().strip()
                    activeDutydict['Branch_Service']= re.sub(pattern_date, '',lst[2]).strip()
                    activeDutydict['Discharge_Type']=lst[3].strip()
                    del lst[1]
                    del lst[1]
                    del lst[1]

                #if Discharge_Type in lst2 and lens == 3
                if len(s) == 3 and '/' in s[0] and '/' in s[1]:
                    activeDutydict['EOD_Date'] = s[0].strip()
                    activeDutydict['RAD_Date'] = s[1].strip()
                    activeDutydict['Branch_Service']=s[2].strip()
                    activeDutydict['Discharge_Type']=lst[2].strip()
                    del lst[1]
                    del lst[1]

                # all in one row and len brach == 1
                if (len(s) == 4 and  '/' in s[0] and '/' in s[1]) and ('/' in lst[2] or 'LEGACY CODES' in lst[2]):
                    activeDutydict['EOD_Date'] = s[0].strip()
                    activeDutydict['RAD_Date'] = s[1].strip()
                    activeDutydict['Branch_Service']=s[2].strip()
                    activeDutydict['Discharge_Type']=s[3].strip()
                    del lst[1]

                # if Discharge_Type in lst2
                if len(s) == 4 and  '/' in s[0] and '/' in s[1] and '/' not in lst[2]  :
                    activeDutydict['EOD_Date'] = s[0]
                    activeDutydict['RAD_Date'] = s[1]
                    activeDutydict['Branch_Service']=s[2]+' '+s[3]
                    activeDutydict['Discharge_Type']=lst[2]
                    del lst[1]
                    del lst[1]
                # All in one row and len branch == 2
                if len(s) == 5 and  '/' in s[0] and '/' in s[1]:
                    activeDutydict['EOD_Date'] = s[0]
                    activeDutydict['RAD_Date'] = s[1]
                    activeDutydict['Branch_Service']=s[2]+' '+s[3]
                    activeDutydict['Discharge_Type']=s[4]
                    del lst[1]

                info_dics.append(activeDutydict.copy())
                activeDutydict['EOD_Date'] = 'None'
                activeDutydict['RAD_Date'] = 'None'
                activeDutydict['Branch_Service']= 'None'
                activeDutydict['Discharge_Type']= 'None'
                continue

            
            del lst[0]


        return info_dics

    #SUBJECT
    def _subject_get(self,data,text=False):
        
        data = ''.join(data).replace('\n','|')
        SUBJECT_TO = ''
        COMBINED_TO = ''

        for i in data.split('|'):
            if SUBJECT_TO != '' and COMBINED_TO != '':
                break
            if 'SUBJECT TO COMPENSATION' in i or "SUBJECT TO COMPENSATION" in i:
                SUBJECT_TO = i
            if 'COMBINED EVALUATION FOR COMPENSATION' in i or 'COMBINED EVALUATION FOR COMPENSATION' in i:
                COMBINED_TO = i
        if SUBJECT_TO == '' or COMBINED_TO == '':
            return "None"

        SUBJECT_AREA = data.split(f'{SUBJECT_TO}')[1].split(f'{COMBINED_TO}')[0]
        lst = SUBJECT_AREA.split('|')
        lst = [i.strip() for i in lst if i.strip() != '']

        #REMOVE CASPIO
        caspio = self._rating_get(data)['CLIENT_CASPIO_FK']
        if caspio.strip() != '':
            lst = [i for  i in  lst if caspio not in i]
        

        # del rating -> copy to
        new_lst = []
        while True:
            
            if 'Rating Decision' not in lst:
                for i in lst:
                    new_lst.append(i)
                break
            
            if 'Rating Decision' in lst[0] and 'Rating Decision' in lst and 'COPY TO'in lst:
                ind1 = lst.index('Rating Decision')
                ind2 = lst.index('COPY TO')
                del lst[ind1:ind2+1]
                continue
            new_lst.append(lst[0])
            del lst[0]
            continue

        lst = new_lst

        
        #SUBJECT 
        new = '|'.join(lst)
        lst = new.split('|')
        list_of_dict = []
        res = {
            'Code':'',
            'Description':'',
            'PercentageDate':''
        }
        if text == True:
            return lst
        while True:
            if len(lst)==0:
                res['Description'] = res['Description'][:257].lstrip().rstrip()
                res1 = res.copy()
                list_of_dict.append(res1)
                break
            if lst[0].strip()=='':
                del lst[0]
                continue
            
            # next code
            if (lst[0].strip()[:4].isnumeric() and res['Code']!='') and  ('(' not in lst[0] and ')' not in lst[0]):
                description = res['Description']
                res['Description'] = description[:257].strip()
                if 'ASSOCIATED' in description:
                    res['Description'] = description.split('ASSOCIATED')[0].strip()
                elif '[' in description:
                    res['Description'] = description.split('[')[0].strip()

                res1 = res.copy()
                list_of_dict.append(res1)

                code_row = lst[0].strip().split()
                if len(code_row) == 1:
                    res['Code'] = lst[0]
                    res['Description']=''
                    res['PercentageDate']=''
                    del lst[0]
                    continue
                if len(code_row) > 1:
                    res['Code'] = code_row[0]
                    desc = ' '.join(code_row[1:])
                    res['Description'] = desc
                    res['PercentageDate']=''
                    del lst[0]
                    continue
            
            if lst[0].lstrip().split()[0].isnumeric() == True and ("("  in lst[0] or ")"  in lst[0]) :
                if  res['Description'] != '':             
                    res['Description'] = res['Description']+' '+lst[0].strip()
                    del lst[0]
                    continue


            #Code
            # if code & desc in one row
            if lst[0][:4].isnumeric() and len(lst[0].strip().split()) > 1 :
                row_code = lst[0].split()
                if row_code[0][:4].isnumeric():
                    res['Code']= row_code[0]
                    desc = ' '.join(row_code[1:])
                    res['Description'] = desc
                    del lst[0]
                    continue
            if len(lst[0].strip().split()) == 1:
                if lst[0][:4].isnumeric(): #and len(lst[0].strip()) == 4 or lst[0][:4].isnumeric() and len(lst[0].strip()) == 9 :#start
                    res['Code']=lst[0]
                    del lst[0]
                    continue

            #Description
            if lst[0].lstrip().split()[0].isupper() == True and res['Description']=='':
                res['Description'] = lst[0]
                del lst[0]
                continue
            if (lst[0].lstrip().split()[0].isupper()  == True or  ('['or']') in lst[0])  and res['Description']!='' :
                res['Description'] = res['Description']+' '+lst[0].strip()
                del lst[0]
                continue
            if res['Description']!= '' and lst[0].strip()[-1] == ']' and res['Description'].count('[') != res['Description'].count(']'):
                res['Description'] = res['Description']+' '+lst[0].strip()
                del lst[0]
                continue
            


            #First percent
            if 'from' in lst[0] and res['PercentageDate']=='':
                res['PercentageDate'] = lst[0].strip()
                del lst[0]
                continue
            #Second percent
            if 'from' in lst[0] and res['PercentageDate']!='':
                res['PercentageDate'] = res['PercentageDate']+' '+lst[0].lstrip().rstrip()
                del lst[0]
                continue

            if res['Description'].count('[') % 2 !=0 and ']' in lst[0]:
                res['Description'] = res['Description']+' '+lst[0].lstrip().rstrip()
            del lst[0]
            continue
        

        #Percent arraw
        for d in list_of_dict:
            date_lst = []
            date_perc = {'percent':'None','date':'None'}
            row = d['PercentageDate'].split()
            while True:
                if len(row)==0:
                    if date_perc['percent'] !='None':
                        date_lst.append(date_perc.copy())
                        break
                    break
                if date_perc['date'] != 'None' and date_perc['percent'] != 'None':
                    date_lst.append(date_perc.copy())
                    if 'End_Date' in date_perc.keys():
                        del date_perc['End_Date'] 
                    date_perc['date'] = 'None'
                    date_perc['percent'] = 'None'
                    if len(row) == 0:
                        break
                    continue

                if '%' in row[0]:
                    date_perc['percent']=row[0].replace('%','')
                    del row[0]
                    continue
                if row[0].count('/') == 2 and 'to' in row and any('%' in element for element in row) == False:

                    to_ind = row.index('to')
                    date_perc['date'] = row[to_ind-1]
                    date_perc['End_Date'] = row[to_ind+1]
                    del row[0]
                    del row[to_ind]
                    continue

                if  row[0].count('/') == 2:
                    if len(row) > 1:
                        if 'to' in row[1]:
                            date_perc['date'] = row[0]
                            date_perc['End_Date'] = row[2]
                            del row[0]
                            del row[1]
                            continue
                    row[0] = row[0].replace(',','')
                    date_perc['date'] = row[0]
                    del row[0]
                    continue
                del row[0]
            d['PercentageDate']=date_lst
        
        #LEFT OR RIGHT
        for row in list_of_dict:
            desc = row['Description']
            if ('LEFT' in desc and 'RIGHT' in desc) or ('Left' in desc and 'Right' in desc) :
                if desc.index('LEFT') < desc.index('RIGHT'):
                    row['Left_or_Right_KW'] = 'LEFT'
                    continue
                if desc.index('LEFT') > desc.index('RIGHT'):
                    row['Left_or_Right_KW'] = 'RIGHT'
                    continue
            if 'LEFT' in desc or 'Left' in desc:
                row['Left_or_Right_KW'] = 'LEFT'
                continue
            if 'RIGHT' in desc or 'Right' in desc:
                row['Left_or_Right_KW'] = 'RIGHT'
                continue

        return list_of_dict

    #GET EVALUTION
    def _evaluation(self,data):

        data = ''.join(data).replace('\n','|')
        if 'SPECIAL MONTHLY COMPENSATION' not in data:
            evaluation_area = data.split('COMBINED EVALUATION FOR COMPENSATION')[1]
            evaluation_area = ''.join(evaluation_area).split('|NOT SERVICE CONNECTED')[0]
            evaluation_area = ''.join(evaluation_area).split('|')
            evaluation_res = [i.strip() for i in evaluation_area if 'from' in i ]
            return evaluation_res
        if 'SPECIAL MONTHLY COMPENSATION' in data:
            evaluation_area = data.split('COMBINED EVALUATION FOR COMPENSATION')[1]
            evaluation_area = ''.join(evaluation_area).split('|SPECIAL MONTHLY')[0]
            evaluation_area = ''.join(evaluation_area).split('|')
            evaluation_res = [i.strip() for i in evaluation_area if 'from' in i ]
            return evaluation_res

    #GET NO COMPESATION
    def _noCompesation(self,data,text=False):
        list_of_dict = []    
        data = ''.join(data).replace('\n','|')
        lst = data.split('|')
        lst = [i for i in lst if i != ' ' and i != '']
        #start no comp area

        while True:
            try:# if NOT SERVICE CONNECTED not in  data:return None
                if 'NOT SERVICE CONNECTED' in lst[0] or 'NOTSERVICECONNECTED' in lst[0]:
                    del lst[0]
                    break
            except IndexError:
                return list_of_dict
            del lst[0]

        caspio = self._rating_get(data)['CLIENT_CASPIO_FK']

        #REMOVE CASPIO
        if caspio.strip() != '':
            lst = [i.strip() for  i in  lst if caspio not in i and i != ''] 

        new_lst = []
        while True:
            
            if 'Rating Decision' not in lst:
                for i in lst:
                    new_lst.append(i)
                break
            
            if 'Rating Decision' in lst[0] and "COPY TO" in lst:
                    ind2 = lst.index('COPY TO')
                    del lst[:ind2+1]
                    continue
            new_lst.append(lst[0])
            del lst[0]
            continue

        lst = new_lst

        res ={
            'Code':'',
            'Description':''
        }
        if text == True:
            return lst
        while True:

            #STOP ITER
            if len(lst)==0:
                if (res['Code'] and res['Code']) != '':
                    res_copy = res.copy()
                    list_of_dict.append(res_copy)
                break
            #next
            if 'Not Service' in lst[0] or "NotService" in lst[0]:
                description = res['Description']
                res['Description'] = description[:257].strip()
                if 'ASSOCIATED' in description:
                    res['Description'] = description.split('ASSOCIATED')[0].strip()
                    description = res['Description']
                elif '[' in description:
                    res['Description'] = description.split('[')[0].strip()

                res_copy = res.copy()
                list_of_dict.append(res_copy)
                res['Code']=''
                res['Description']=''
                del lst[0]
                continue
            
            # #STOP KEYS
            # if 'ANCILLARY' in lst[0] or 'TREATMENT PURPOSES ONLY' in lst[0] or 'NOT SERVICE CONNECTED' in lst[0] or '____' in lst[0]:
            #     break
            
            strings_to_check = ('DEFERRED ISSUES','TREATMENT PURPOSES ONLY', 'NOT SERVICE CONNECTED', 'DEFERRED ISSUES', '___')

            if any(string in lst[0] for string in strings_to_check):
                break

            #Code
            # if code & desc in one row
            if lst[0][:4].isnumeric() and len(lst[0].strip().split()) > 1 :
                row_code = lst[0].split()
                if row_code[0][:4].isnumeric():
                    res['Code']= row_code[0]
                    desc = ' '.join(row_code[1:])
                    res['Description'] = desc
                    del lst[0]
                    continue
            if len(lst[0].strip().split()) == 1:
                if lst[0][:4].isnumeric(): #and len(lst[0].strip()) == 4 or lst[0][:4].isnumeric() and len(lst[0].strip()) == 9 :#start
                    res['Code']=lst[0]
                    del lst[0]
                    continue

            #DESCRIPTION
            if (lst[0].lstrip().split()[0].isupper() == True and res['Description']== '') and res['Code'] != '':
                res['Description'] = lst[0].rstrip()
                del lst[0]
                continue
            if ((lst[0].lstrip().split()[0].isupper() == True  or  ('[' or ']'or '(' or ')') in lst[0]) and res['Description']!='') and res['Code'] != '':
                res['Description'] = res['Description']+' '+lst[0].strip()
                del lst[0]
                continue



            if res['Description'].count('[') % 2 !=0 and ']' in lst[0]:
                res['Description'] = res['Description']+' '+lst[0].strip()
            del lst[0]
            continue



        #LEFT OR RIGHT
        for row in list_of_dict:
            desc = row['Description']
            if ('LEFT' in desc and 'RIGHT' in desc) or ('Left' in desc and 'Right' in desc) :
                if desc.index('LEFT') < desc.index('RIGHT'):
                    row['Left_or_Right_KW'] = 'LEFT'
                    continue
                if desc.index('LEFT') > desc.index('RIGHT'):
                    row['Left_or_Right_KW'] = 'RIGHT'
                    continue
            if 'LEFT' in desc or 'Left' in desc:
                row['Left_or_Right_KW'] = 'LEFT'
                continue
            if 'RIGHT' in desc or 'Right' in desc:
                row['Left_or_Right_KW'] = 'RIGHT'
                continue

        return list_of_dict
    


        #JSON FILE CREATOR
    
    #DEFERRED Issues
    def _get_deferredIssues(self,data,text=False):
        list_of_dict = []    
        data = ''.join(data).replace('\n','|')
        lst = data.split('|')
        lst = [i for i in lst if i != ' ' and i != '']

        while True:
            try:# if NOT SERVICE CONNECTED not in  data:return None
                if 'DEFERRED ISSUES' in lst[0] or 'DEFERREDISSUES' in lst[0]:
                    del lst[0]
                    break
            except IndexError:
                return list_of_dict
            del lst[0]

        caspio = self._rating_get(data)['CLIENT_CASPIO_FK']

        #REMOVE CASPIO
        if caspio.strip() != '':
            lst = [i.strip() for  i in  lst if caspio not in i and i != ''] 

        new_lst = []
        while True:
            
            if 'Rating Decision' not in lst:
                for i in lst:
                    new_lst.append(i)
                break
            
            if 'Rating Decision' in lst[0] and "COPY TO" in lst:
                    ind2 = lst.index('COPY TO')
                    del lst[:ind2+1]
                    continue
            new_lst.append(lst[0])
            del lst[0]
            continue

        lst = new_lst

        res ={
            'Code':'',
            'Description':''
        }
        if text == True:
            return lst
        while True:

            #STOP ITER
            if len(lst)==0:
                if (res['Code'] and res['Code']) != '':
                    res_copy = res.copy()
                    list_of_dict.append(res_copy)
                break
            #next
            if 'Not Service' in lst[0] or "NotService" in lst[0] or "Static Disability" in lst[0] or "StaticDisability" in lst[0]:
                description = res['Description']
                res['Description'] = description[:257].strip()
                if 'ASSOCIATED' in description:
                    res['Description'] = description.split('ASSOCIATED')[0].strip()
                    description = res['Description']
                elif '[' in description:
                    res['Description'] = description.split('[')[0].strip()
                res_copy = res.copy()
                list_of_dict.append(res_copy)

                res['Code']=''
                res['Description']=''
                del lst[0]
                continue
            
            # #STOP KEYS
            # if 'ANCILLARY' in lst[0] or 'TREATMENT PURPOSES ONLY' in lst[0] or 'NOT SERVICE CONNECTED' in lst[0] or '____' in lst[0]:
            #     break
            
            strings_to_check = ('DEFERRED ISSUES','TREATMENT PURPOSES ONLY', 'NOT SERVICE CONNECTED', 'DEFERRED ISSUES', '___')

            if any(string in lst[0] for string in strings_to_check):
                break

            #Code
            # if code & desc in one row
            if lst[0][:4].isnumeric() and len(lst[0].strip().split()) > 1 :
                row_code = lst[0].split()
                if row_code[0][:4].isnumeric():
                    res['Code']= row_code[0]
                    desc = ' '.join(row_code[1:])
                    res['Description'] = desc
                    del lst[0]
                    continue
            if len(lst[0].strip().split()) == 1:
                if lst[0][:4].isnumeric(): #and len(lst[0].strip()) == 4 or lst[0][:4].isnumeric() and len(lst[0].strip()) == 9 :#start
                    res['Code']=lst[0]
                    del lst[0]
                    continue

            #DESCRIPTION
            if (lst[0].lstrip().split()[0].isupper() == True and res['Description']== '') and res['Code'] != '':
                res['Description'] = lst[0].rstrip()
                del lst[0]
                continue
            if ((lst[0].lstrip().split()[0].isupper() == True  or  ('[' or ']'or '(' or ')') in lst[0]) and res['Description']!='') and res['Code'] != '':
                res['Description'] = res['Description']+' '+lst[0].strip()
                del lst[0]
                continue



            if res['Description'].count('[') % 2 !=0 and ']' in lst[0]:
                res['Description'] = res['Description']+' '+lst[0].strip()
            del lst[0]
            continue

        #LEFT OR RIGHT
        for row in list_of_dict:
            desc = row['Description']
            if ('LEFT' in desc and 'RIGHT' in desc) or ('Left' in desc and 'Right' in desc) :
                if desc.index('LEFT') < desc.index('RIGHT'):
                    row['Left_or_Right_KW'] = 'LEFT'
                    continue
                if desc.index('LEFT') > desc.index('RIGHT'):
                    row['Left_or_Right_KW'] = 'RIGHT'
                    continue
            if 'LEFT' in desc or 'Left' in desc:
                row['Left_or_Right_KW'] = 'LEFT'
                continue
            if 'RIGHT' in desc or 'Right' in desc:
                row['Left_or_Right_KW'] = 'RIGHT'
                continue

        return list_of_dict

    #DECISION
    def _get_Decision(self,data,text=False):
        res ={}
        list_of_dict = []    
        caspioAndDate = self._rating_get(data)
        caspioID = caspioAndDate['CLIENT_CASPIO_FK']
        headerDate  = caspioAndDate['HEADER_DATE']
        data = ''.join(data).replace('|',' ')
        data = re.sub(re.escape(caspioID), '', data)
        data = re.sub(re.escape(headerDate), '', data)
        if "DECISIONS" in data:
            data = data.replace('DECISIONS','')
        data =  data.split('DECISION')[1].split('EVIDENCE')[0]
        pattern = r'(?<=\d\.\s)'

        sentences = re.split(pattern, data)

        data = [sentence.strip() for sentence in sentences if sentence.strip()]
        data = [item for item in data if not item.replace('.','').strip().isdigit()]
        if text == True:
            return data
        for row in data:
            match_name = re.search(r'(?i)(?:(?:evaluation\s*for|Entitlement\s*to\s*an\s*earlier\s*effective\s*date\s*for\s*service\s*connection\s*for|The\s*previous\s*denial\s*of\s*service\s*connection\s*for)|(?:The\s*claim\s*for\s*service\s*connection\s*for)|(?:Evaluation\s*of)|(?:A\s*decision\s*on\s*entitlement\s*to\s*compensation\s*for)|(?:Service\s*connection\s*for))\s+(.+?)\s+(?:is\s*confirmed|as\s*secondary\s*to|remains\s*denied\s*b|which\s*is\s*currently|is\s*granted|is\s*denied|is\s*deferred)', row)
            if match_name:
                decisionName = match_name.group(1)
                if '(' in decisionName:
                    decisionName = decisionName.split('(')[0]
                elif '[' in decisionName:
                    decisionName = decisionName.split('[')[0]
                res['DecisionName'] = decisionName
                
            match_evaluation = re.search(r'(?:A\s*|as\s*secondary\s*to|which\s*is\s*currently|is\s*granted\s*with\s*an\s*evaluation\s*of)\s+(\d+)\s+(?:percent\s*evaluation\s*has\s*been\s*assigned|confirmed\s*and\s*continued|percent\s*disabling|percent\s*effective)', row)
            if match_evaluation:
                res['DecisionEvalution'] = match_evaluation.group(1)

            match_date = re.search(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b', row)
            if match_date:
                res['EffDate'] = match_date.group()
            
            list_of_dict.append(res.copy())
            res = {}


        return list_of_dict
    
    #JSON
    def _create_data_for_json(self,rating_res,active_res,subject_res,no_compes,deferredIssues,get_Decision):
        js = {
            'Veteran': {
                'Name': rating_res['Veterane_name'],
                'VA File Number': rating_res['Va_File_Number'],
                'Social Security Number': rating_res['SOCIAL SECURITY NR'],
                'POA': rating_res['POA'],
                'CLIENT_CASPIO_FK': rating_res['CLIENT_CASPIO_FK'],
                'HEADER_DATE': rating_res['HEADER_DATE'],
                'Service Information': {
                    'Service Dates': active_res
                },
                'Compensation Information': {
                    'Compensation': subject_res,
                    'No Compensation': no_compes
                },
                'Deferred Issues': deferredIssues,
                'Decision': get_Decision
            }
        }
        with open('file.json', 'w') as f:
            json.dump(js, f, indent=4)


if __name__ == '__main__':
    print("*******************************************")
    print("*                  *                      *")
    print("*      Welcome to the PDF Scraper!        *")
    print("*                  *                      *")
    print("*          Created by Workmovr            *")
    print("*                  *                      *")
    print("*******************************************")

    parser = argparse.ArgumentParser()
    parser.add_argument('--argument', required=False)

    args = parser.parse_args()
    argument_value = args.argument
    print(argument_value)
    parserPDF = PDFParser(argument_value)
    
    
    # path = '/Users/edgarlalayan/Desktop/CASPIO/Veteran /parser1.5/McKeown Law -- RatingDecisionExtract Project/Sample RatingDecisions/RatingDecision - 01-17-2023 - 4HPGK2FV.pdf'
    # parser  = PDFParser()
    # parser.process_pdf_files()

    # parser.text_file(path)




#CHECK WITH EKATERINA
#path = '/Users/edgarlalayan/Desktop/CASPIO/Veteran /parser1.5/McKeown Law -- RatingDecisionExtract Project/Sample RatingDecisions/RatingDecision - 02-06-2023 - SOIVWYE8.pdf'
#A difference
#path = '/Users/edgarlalayan/Desktop/CASPIO/Veteran /parser1.5/McKeown Law -- RatingDecisionExtract Project/Sample RatingDecisions/RatingDecision - 3-10-2023 - UVN6JWA5.pdf'
