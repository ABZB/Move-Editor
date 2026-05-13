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

def reconstruct_GARC(poke_edit_data, GARC_name):
    
    match GARC_name:
        case "personal":
            #merges concatenated file for output
            out_file = poke_edit_data.personal + [reduce(lambda i, j: i+j, poke_edit_data.personal)]
        case "evolution":
            out_file = poke_edit_data.evolution
        case "levelup":
            out_file = poke_edit_data.levelup
        case "model":
            #merges with header for output
            out_file = [poke_edit_data.model_header] + poke_edit_data.model
            
    file_count = len(out_file)

    temp = [0x0]*0x1C
    FAT0_offset = 0

    #magic GARC
    temp[0:4] = [0x43, 0x52, 0x41, 0x47]

    #Endian
    temp[0x08:0xA] = [0xFF, 0xFE]

    #header length and Version
    if(poke_edit_data in {"XY", "ORAS"}):
        temp[0x4] = 0x1C
        temp[0xB] = 0x04
        FAT0_offset = 0x1C
    else:
        temp[0x4] = 0x24
        temp[0xB] = 0x06
        temp.extend([0]*8)
        FAT0_offset = 0x24

    #section count
    temp[0xC] = 0x4

    #FAT0 Header allocation
    temp.extend([0]*(0xC + 4*file_count))
    
    #Magic FAT0
    temp[FAT0_offset:FAT0_offset + 4] = [0x4F, 0x54, 0x41, 0x46]
    
    #FAT0 length
    temp[FAT0_offset + 0x4:FAT0_offset + 0x8] = from_int_little_bytes(file_count*4 + 0xC, 0x4)

    #file count
    temp[FAT0_offset + 0x8:FAT0_offset + 0xA] = from_int_little_bytes(file_count, 0x2)

    #padding
    temp[FAT0_offset + 0xA:FAT0_offset + 0xC] = [0xFF, 0xFF]

    #write FAT0 thing
    pointer = FAT0_offset + 0xC
    for x in range(file_count):
        temp[pointer:pointer + 4] = from_int_little_bytes(x * 0x10, 0x4)
        pointer += 0x4


    #allocate BFAT, 0xC for header, then 0x10 per file
    temp.extend([0]*(0xC + 0x10*file_count))
    #magic BFAT
    temp[pointer:pointer + 4] = [0x42, 0x54, 0x41, 0x46]

    pointer +=4

    #BFAT length
    temp[pointer:pointer + 4] = from_int_little_bytes(file_count*0x10 + 0xC, 0x4)

    pointer +=4

    #BFAT file count
    temp[pointer:pointer + 2] = temp[FAT0_offset + 0x8:FAT0_offset + 0xA]

    pointer += 4

    #before we write the BFAT blocks, add the FIMB header so we can write those blocks and actual files at once

    #this will point at end of file
    fimb_pointer = len(temp)

    temp.extend([0]*(0xC))
    
    #magic FIMB
    temp[fimb_pointer :fimb_pointer  + 4] = [0x42, 0x4D, 0x49, 0x46]
    
    fimb_pointer  += 4

    #FIMB header length (3 high bytes are zero)
    temp[pointer] = [0x0C]


    #need to update this with final offset below
    fimb_pointer  += 4


    data_pointer = len(temp)

    #update GARC header with data start

    temp[0x10:0x14] = from_int_little_bytes(data_pointer, 0x4)

    offset = 0
    biggest_size = 0
    biggest_size_padding = 0
    for file in out_file:
        
        #padding
        temp[pointer:pointer + 4] = [0x01, 0x00, 0x00, 0x00]

        #offset start
        temp[pointer + 4: pointer + 8] = from_int_little_bytes(offset, 0x4)

        length = len(file)
        
        
        biggest_size = max(length, biggest_size)
        padding = (length - 4) % 4
        biggest_size_padding = max(length + padding, biggest_size_padding)
        offset += length + padding

        #offset end. When there is padding to z bytes, those extra bytes are filled with 0xFF, are NOT counted in the length, but ARE counted in the end-address
        temp[pointer + 8: pointer + 0xC] = from_int_little_bytes(offset, 0x4)

        #length
        temp[pointer + 0xC: pointer + 0x10] = from_int_little_bytes(length, 0x4)


        #extend temp by length of file
        temp.extend([0]*length)
        #write file to location
        temp[data_pointer: data_pointer + length] = file

        if(padding != 0):
            temp.extend([0xFF]*padding)

        data_pointer += length + padding

        pointer += 0x10

    #write total length of files
    temp[fimb_pointer:fimb_pointer + 4] = from_int_little_bytes(offset, 0x4)

    #in GARC header, need to write file length, and largest file size (plus padded max and padding in gen 7)

    #only write largest file size at FAT0_offset - 4
    if(poke_edit_data in {"XY", "ORAS"}):
        temp[FAT0_offset - 0x4:FAT0_offset] = from_int_little_bytes(biggest_size, 0x4)
    
    #starting from FAT0_offset - 0xC:
    #max of 0x4 and max file size
    #max file size
    #padding (0x4)
    else:
        temp[FAT0_offset - 0xC:FAT0_offset - 0x8] = from_int_little_bytes(biggest_size_padding, 0x4)
        temp[FAT0_offset - 0x8:FAT0_offset - 0x4] = from_int_little_bytes(biggest_size, 0x4)
        temp[FAT0_offset - 0x4:FAT0_offset] = from_int_little_bytes(0x4, 0x4)

    #write total length of entire GARC
    temp[0x14:0x18] = from_int_little_bytes(len(temp), 0x4)


    return(temp)

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
                case "Levelup":
                    poke_edit_data.levelup_path = garc_path
                    poke_edit_data.levelup = file_array

                case "Evolution":
                    poke_edit_data.evolution_path= garc_path
                    poke_edit_data.evolution = file_array
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