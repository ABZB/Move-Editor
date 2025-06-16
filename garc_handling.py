import csv
from tkinter.filedialog import askdirectory, asksaveasfilename, askopenfilename
from utilities import *
from functools import reduce

def binary_file_to_array(file_path):

    with open(file_path, "r+b") as f:
        f.seek(0, os.SEEK_END)
        file_end = f.tell()
        f.seek(0, 0)
        return(list(f.read(file_end)))

def deconstruct_GARC(bindata, poke_edit_data):
        #header:
        # 0x4 Header length (4 bytes)
        # 0x10 Data start (4 bytes)
        # 0x14 total file length (4 bytes)

        #then depends on version
        
        # V4
        # 0x18 largest file size (unpadded)

        # V6

        # 0x18 largest file size (with padding if it exists)
        # 0x1C largest file size (without padding, virtually always equal to the above for our purposes)
        # 0x20 Padding value (usually 0x4)

        #counting from end of whatever version you're in (so 0x4 = 0x1C in v4, 0x24 in v6)

        # 0x8 FAT0 header length (counting from 0x4)
        # 0xC, number of files (2 bytes)
        # from 0x10, 4 bytes per file, each one is 0x10 times file number (start from 0)
        

        #from end of above, 0x4 - header length
        # 0x8 - file count, then 
        # then for each file, 0x01 00 00 00, then offset start, offset end, and file length, offset counting first byte of first file as 0x0

        #finally, last magic word, then header length (0xC), then length of actual data (same as final offset end from previous section

        #get Fat0 offset
        FAT0_offset = 0
        if(poke_edit_data.game in {"XY", "ORAS"}):
           FAT0_offset = 0x1C
        else:
           FAT0_offset = 0x24
        
        
        FATB_offset = FAT0_offset + from_little_bytes_int(bindata[FAT0_offset + 0x4:FAT0_offset + 0x8])

        file_count = from_little_bytes_int(bindata[FAT0_offset + 0x8:FAT0_offset + 0xA])

        data_absolute_offset = from_little_bytes_int(bindata[0x10:0x14])


        output_array = []

        #0xC is start of the actual file location/length data.
        FATB_offset += 0xC

        #iterate over the files, pulling the length from the FATB data, each file gets its own array in temp
        for _ in range(file_count):
            
            #move data pointer to start of next file
            data_offset = data_absolute_offset + from_little_bytes_int(bindata[FATB_offset + 0x4:FATB_offset + 0x8])
            #print(data_offset)
            #get length of current file
            file_length = from_little_bytes_int(bindata[FATB_offset + 0xC:FATB_offset + 0x10])

            #append the file to a new entry in output array
            output_array.append(bindata[data_offset:data_offset + file_length])
            

            #the offset end is different than start + length because length is padded to multiple of 4.

            #move to next file in FATB data
            FATB_offset += 0x10

        return(output_array)

def save_GARC(poke_edit_data, GARC_name):

    temp = reconstruct_GARC(poke_edit_data, GARC_name)

    match GARC_name:
        case "personal":
            file_path = poke_edit_data.personal_path
        case "evolution":
            file_path = poke_edit_data.evolution_path
        case "levelup":
            file_path = poke_edit_data.levelup_path
        case "model":
            file_path = poke_edit_data.model_path

    with open(file_path, "w+b") as f:
        f.write(bytes(temp))


#loads list of filenames in extracted GARC if it exists, otherwise return empty array
def load_GARC(poke_edit_data, garc_path, target, gameassert):

    if(os.path.exists(garc_path)):
        poke_edit_data.game = gameassert

        try:
            file_array = deconstruct_GARC(binary_file_to_array(garc_path), poke_edit_data)

            match poke_edit_data.game:
                case "XY":
                    poke_edit_data.max_species_index = 721
                case "ORAS":
                    poke_edit_data.max_species_index = 721
                case "SM":
                    poke_edit_data.max_species_index = 802
                case "USUM":
                    poke_edit_data.max_species_index = 807

            match target:
                case "Personal":
                    poke_edit_data.personal_path = garc_path

                    #delete compilation file
                    file_array.pop()

                    poke_edit_data.personal = file_array
                    poke_edit_data = update_species_list(poke_edit_data)
                case "Levelup":
                    poke_edit_data.levelup_path = garc_path
                    poke_edit_data.levelup = file_array

                case "Evolution":
                    poke_edit_data.evolution_path= garc_path
                    poke_edit_data.evolution = file_array
                case "Model":
                    poke_edit_data.model_path = garc_path
                    #pop model header into its own file
                    poke_edit_data.model_header = file_array.pop(0)
                    poke_edit_data.model = file_array
                    poke_edit_data = update_model_list(poke_edit_data)
        except Exception as e:
            print(e)
            return(poke_edit_data)

    else:
        print("Garc folder not found, unreadable, or empty")
    return(poke_edit_data)

def choose_GARC(poke_edit_data, target, gameassert):
    
    targetpath = ''
    #Evolution table has a fixed length per personal file, 0x30 in gen VI, 0x40 in gen VII
    #Similarly, the Personal file itself is 0x50 in gen VI, 0x54 in gen VII (additional bytes for "is regional forme" and Species-specific Z move)
    match gameassert:
        case "XY":
            poke_edit_data.evolution_table_length = 0x30
            poke_edit_data.personal_table_length = 0x50
            match target:
                case "Model":
                    targetpath = '0/0/7'
                case "Personal":
                    targetpath = '2/1/8'
                case "Levelup":
                    targetpath = '2/1/4'
                case "Evolution":
                    targetpath = '2/1/5'
            poke_edit_data.modelless_exists = False
        case "ORAS":
            poke_edit_data.evolution_table_length = 0x30
            poke_edit_data.personal_table_length = 0x50
            match target:
                case "Model":
                    targetpath = '0/0/8'
                case "Personal":
                    targetpath = '1/9/5'
                case"Levelup":
                    targetpath = '1/9/1'
                case"Evolution":
                    targetpath = '1/9/2'
            poke_edit_data.modelless_exists = False
        case "SM":
            poke_edit_data.evolution_table_length = 0x40
            poke_edit_data.personal_table_length = 0x54
            match target:
                case"Model":
                    targetpath = '0/9/3'
                case"Personal":
                    targetpath = '0/1/7'
                case"Levelup":
                    targetpath = '0/1/3'
                case"Evolution":
                    targetpath = '0/1/4'
            poke_edit_data.modelless_exists = False
        case "USUM":
            poke_edit_data.evolution_table_length = 0x40
            poke_edit_data.personal_table_length = 0x54
            match target:
                case"Model":
                    targetpath = '0/9/4'
                case"Personal":
                    targetpath = '0/1/7'
                case"Levelup":
                    targetpath = '0/1/3'
                case"Evolution":
                    targetpath = '0/1/4'
        case "Select Game":
               print("Error: Game not set")
               return



    folder_path = askopenfilename(title='Select ' + target + ' GARC, a/' + targetpath)
    poke_edit_data = load_GARC(poke_edit_data, folder_path, target, gameassert)
    
    return(poke_edit_data)

             
#loads the data from the filepath in the class data structure to the correct variables
def load_names_from_CSV(poke_edit_data, just_wrote = False):
    
    
    temp_base_species_list =  []
    temp_master_formes_list = []
    temp_model_source_list = []
    temp_loaded_csv = []

    try:
        with open(poke_edit_data.csv_pokemon_list_path, newline = '', encoding='utf-8-sig') as csvfile:
            reader_head = csv.reader(csvfile, dialect='excel', delimiter=',')
        
            #load csv into an array      
            loaded_csv_file = list(reader_head)
        
            #check to see if older version from before saving the model header bytes and removes the header row
            try:
                if(loaded_csv_file.pop(0)[14] == 'Model Bitflag 1'):
                    has_bitflag = True
                else:
                    has_bitflag = False
            except Exception as e:
                print('Error when trying to check for model bitflag in CSV, ', e)
                has_bitflag = False

    return(poke_edit_data)

#just asks for the path and calls the write-csv-to-the-right-part-of-the-class-data-structure program
def user_prompt_load_CSV(poke_edit_data, target):

    poke_edit_data.csv_pokemon_list_path = askopenfilename(title='Select ' + target + ' CSV')
    

    poke_edit_data = load_names_from_CSV(poke_edit_data)
    

    return(poke_edit_data)



def write_CSV(poke_edit_data, csv_path = ''):

    #use saved config path if nothing set
    if(csv_path == ''):
        csv_path = poke_edit_data.csv_pokemon_list_path
    else:
        poke_edit_data.csv_pokemon_list_path = csv_path

    try:
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer_head = csv.writer(csvfile, dialect='excel', delimiter=',')
            #write the header line
            writer_head.writerow (['Base Index', 'Personal Index', 'Model Index', 'Species', 'Forme', 'Model', 'Texture', 'Shiny_Texture', 'Greyscale_Texture', 'Battle_Animations', 'Refresh_Animations', 'Movement_Animations', 'Lip_Animations', 'Empty', 'Model Bitflag 1', 'Model Bitflag 2', 'Portrait', 'Shiny_Portrait', 'Icon'])
            
            if(poke_edit_data.game in {'SM', 'USUM'}):
                model_file_start = 1
                model_file_count = 9                
            else:
                model_file_count = 8
                
                if(poke_edit_data.game == 'XY'):
                    model_file_start = 4
                else:
                    model_file_start = 3
                
            #print(len(poke_edit_data.master_list_csv))
            #iterate over the names in the model source list
            #write species index to column A, personal file index to B, model index to C, species name to D, forme to E, then model/texture/animaiton filenames in 6 starts at 4, 3, 1 for XY, ORAS, SMUSUM
            for enum, pokemon_instance in enumerate(poke_edit_data.master_list_csv):
                if(enum == 0):
                    writer_head.writerow ([pokemon_instance[2], pokemon_instance[3], pokemon_instance[4], pokemon_instance[0], pokemon_instance[1]] + ['' for x in range(model_file_count)] + ['', ''])
                else:
                    #print([pokemon_instance[2], pokemon_instance[3], pokemon_instance[4], pokemon_instance[0], pokemon_instance[1]] + [(enum - 1)*model_file_count + x + model_file_start for x in range(model_file_count)])
                    if(poke_edit_data.game in {'SM', 'USUM'}):
                        writer_head.writerow ([pokemon_instance[2], pokemon_instance[3], pokemon_instance[4], pokemon_instance[0], pokemon_instance[1]] + [(enum - 1)*model_file_count + x + model_file_start for x in range(model_file_count)] + [pokemon_instance[5], pokemon_instance[6]])
                    else:
                        writer_head.writerow ([pokemon_instance[2], pokemon_instance[3], pokemon_instance[4], pokemon_instance[0], pokemon_instance[1]] + [(enum - 1)*model_file_count + x + model_file_start for x in range(model_file_count)] + '' + [pokemon_instance[5], pokemon_instance[6]])
                        
    #don't do anything and proceed as usual if none exists, print error message
    except Exception as e:
        print(e, 'If this error message is thrown and the CSV has all the Pokemon in it, everything is fine, not sure why this error is happening')#'Selected CSV file is open in another program. Please close it and try again')
    
    
    #print('after write')
    #for pokemon_instance in poke_edit_data.master_list_csv:
    #    print(pokemon_instance)
    return(poke_edit_data)