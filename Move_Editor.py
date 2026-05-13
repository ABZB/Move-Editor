from garc_handling import *
from utilities import *
from my_constants import *


def export_tmhmtutor(move_edit_data, move_list, pokemon_list):

    #load person GARC
    move_edit_data = choose_GARC(move_edit_data, 'Personal', move_edit_data.game)

    tutor_compat_table = []
    tmhm_compat_table = []
    
    with open(askopenfilename(title='Select code.bin', defaultextension='.bin',filetypes= [('BIN','.bin')]), "r+b") as f:
        f.seek(0x004E6860, 0)

        #vanilla
        for x in range(68):
            temp = from_little_bytes_int(list(f.read(2)))
            tutor_compat_table.append(temp) if (temp < len(move_list) and temp != 0) else ''
        #added
        if(tutor_compat_table[-1] != 0xFFFF):
            f.seek(0x004BB7BE, 0)
            for x in range(84):
                temp = from_little_bytes_int(list(f.read(2)))
                if(temp > len(move_list) or temp == 0):
                    break
                else:
                    tutor_compat_table.append(temp)
        #add first 107
        f.seek(0x004BB98E,0)
        for x in range(107):
            tmhm_compat_table.append(from_little_bytes_int(list(f.read(2))))

        #check if vanilla or expanded TM list
        f.seek(0x00275E04,0)
        #check not vanilla
        if(from_little_bytes_int(list(f.read(4))) != 0xE1D3C0B0):
            f.seek(0x004BB794,0)
            for x in range(21):
                temp_tm = from_little_bytes_int(list(f.read(2)))
                if(temp_tm == 0 or temp_tm > len(move_list)):
                    break
                tmhm_compat_table.append(temp_tm)


    special_tutors = [520, 519, 518, 338, 307, 308, 434, 620]

    #choose output path for dump
    save_path = asksaveasfilename(title='Save exported table of TM/HM & Tutor Moves', defaultextension='.csv',filetypes= [('CSV','.csv')])

    with open(save_path, 'w', newline = '', encoding='utf-8-sig') as csvfile:
        writer_head = csv.writer(csvfile, dialect='excel', delimiter=',')

        header_row = ['Personal Index', 'Name']

        for x, move in enumerate(tmhm_compat_table):
            header_row.append(f'TM{x + 1:03d}: {move_list[move]}')

        for x, move in enumerate(tutor_compat_table):
            header_row.append(f'TUT{x + 1:03d}: {move_list[move]}')

        for x, move in enumerate(special_tutors):
            header_row.append(f'SPE{x + 1}: {move_list[move]}')

        #write the header line
        writer_head.writerow(header_row)

        #iterate over all files
        for index, file in enumerate(move_edit_data.personal):
            temp_row = [index, pokemon_list[index]]

            #do tms, 0x28-0x37 (count 16)
            for x in range(len(tmhm_compat_table)):
                if(file[0x28 + (x>>3)] & (1 << (x%8)) == 0):
                    temp_row.append('')
                else:
                    temp_row.append(1)

            #do regular tutors
            for x in range(min(128,len(tutor_compat_table))):
                if(file[0x3C + (x>>3)] & (1 << (x%8)) == 0):
                    temp_row.append('')
                else:
                    temp_row.append(1)

            if(len(tmhm_compat_table) > 128):
                for x in range(len(tmhm_compat_table) - 128):
                    if(file[0x39 + (x>>3)] & (1 << (x%8)) == 0):
                        temp_row.append('')
                    else:
                        temp_row.append(1)

            #do special tutors
            for x in range(8):
                if(file[0x38] & (1 << x) == 0):
                    temp_row.append('')
                else:
                    temp_row.append(1)

            writer_head.writerow(temp_row)



def import_tmhmtutor(move_edit_data, move_list):

    temp_array = []

    #choose edited .csv
    save_path = askopenfilename(title='Choose edited table of Level-Up Moves', defaultextension='.csv',filetypes= [('CSV','.csv')])

    #load Personal GARC
    move_edit_data = choose_GARC(move_edit_data, 'Personal', move_edit_data.game)

    #get data from csv individual binary files
    with open(save_path, 'r', newline = '', encoding='utf-8-sig') as csvfile:
        reader_head = csv.reader(csvfile, dialect='excel', delimiter=',')

        temp_array = list(reader_head)




    #build the new set of binary files

    last_personal = 0

    temp_file = []

    tm_tutor_special = [[], [], []]

    for line_number, line in enumerate(temp_array):
        #no file for blank space
        if(line[0] == ''):
            pass
        #store move names per category
        elif(line[0] == 'Personal Index'):
            for x in line[2:]:
                if(x[:2] == 'TM'):
                    tm_tutor_special[0].append(x[7:])
                elif(x[:3] == 'TUT'):
                    tm_tutor_special[1].append(x[8:])
                elif(x[:3] == 'SPE'):
                    tm_tutor_special[2].append(x[6:])
                else:
                    print(f'Warning, error, {x} is not right.')

        #valid Pokemon line
        else:


            
            tm_byte = 0x28
            temp_byte = 0

            #do TM
            for x, _ in enumerate(tm_tutor_special[0]):
                #xth tm in this list is at x+2 in the row

                #if TM is set, set its bitflag, skip first two columns in this line as those are personal index and name
                if(line[x+2] in {1, '1', 'true', 'TRUE', 'True', 'y', 'Y'}):
                    temp_byte += 1 << (x%8)

                #if end of TM list or finished byte (x%8 = 7), write byte
                if(x + 1 == len(tm_tutor_special[0]) or x%8 == 7):
                    
                    #set byte in personal
                    move_edit_data.personal[line_number - 1][tm_byte] = temp_byte
                    #reset temp byte
                    temp_byte = 0
                    #increment tm byte
                    tm_byte += 1


            tm_byte = 0x3C
            temp_byte = 0
            #BP Tutors
            for x, _ in enumerate(tm_tutor_special[1]):
                #xth turor in this list is at (x + # TMs + 2) in the row

                #if tutor is set, set its bitflag, skip first two columns in this line as those are personal index and name
                if(line[x + len(tm_tutor_special[0]) +  2] in {1, '1', 'true', 'TRUE', 'True', 'y', 'Y'}):
                    temp_byte += 1 << (x%8)

                #if end of tutor list or finished byte (x%8 = 7), write byte
                if(x + 1 == len(tm_tutor_special[1]) or x%8 == 7):
                    
                    #set byte in personal
                    move_edit_data.personal[line_number - 1][tm_byte] = temp_byte
                    #reset temp byte
                    temp_byte = 0
                    #increment or move byte
                    if(tm_byte == 0x47):
                        tm_byte = 0x39
                    else:
                        tm_byte += 1


            tm_byte = 0x38
            temp_byte = 0
            #Special Tutors
            for x, _ in enumerate(tm_tutor_special[2]):
                #xth turor in this list is at (x + # TMs + 2) in the row

                #if tutor is set, set its bitflag, skip first two columns in this line as those are personal index and name
                if(line[x + len(tm_tutor_special[0]) + len(tm_tutor_special[1]) +  2] in {1, '1', 'true', 'TRUE', 'True', 'y', 'Y'}):
                    temp_byte += 1 << (x%8)

                #if end of tutor list or finished byte (x%8 = 7), write byte
                if(x + 1 == len(tm_tutor_special[2]) or x%8 == 7):
                    
                    #set byte in personal
                    move_edit_data.personal[line_number - 1][tm_byte] = temp_byte
                    #reset temp byte
                    temp_byte = 0
                    #increment or move byte
                    if(tm_byte == 0x47):
                        tm_byte = 0x39
                    else:
                        tm_byte += 1

            #we have written everything for this Pokemon, on to next one


    save_GARC(move_edit_data, 'personal')

    return(move_edit_data)

def export_levelup(move_edit_data, move_list, pokemon_list):

    #load levelup GARC
    move_edit_data = choose_GARC(move_edit_data, 'Levelup', move_edit_data.game)

    #choose output path for dump
    save_path = asksaveasfilename(title='Save exported table of Level-Up Moves', defaultextension='.csv',filetypes= [('CSV','.csv')])

    with open(save_path, 'w', newline = '', encoding='utf-8-sig') as csvfile:
        writer_head = csv.writer(csvfile, dialect='excel', delimiter=',')

        #write the header line
        writer_head.writerow (['Personal Index', 'Name', 'Level', 'Move'])

        #iterate over all files
        for index, file in enumerate(move_edit_data.levelup):
            for entry_index in range(len(file)//4):
                move_index = from_little_bytes_int(file[entry_index*4:entry_index*4 + 2])
                level = file[entry_index*4 + 2]

                #don't edit terminator
                if(level == 0xFF and move_index == 0xFFFF):
                    pass
                else:
                    try:
                        writer_head.writerow ([index, pokemon_list[index], level, move_list[move_index]])
                    except Exception as e:
                        print(e)
                        if(index >= len(pokemon_list)):
                            print('You might be using the wrong generation, or have added additional Pokemon/formes. In the latter case, update the appropriate CSV.')
                        if(move_index >= len(move_list)):
                            print('You might have added additional moves, in that case, please add them in the appropriate place in move_list.csv')

            #write blank line after every Pokemon for easy reading
            writer_head.writerow (['', '', '', ''])

def import_levelup(move_edit_data, move_list):

    output_array = []

    temp_array = []

    #choose edited .csv
    save_path = askopenfilename(title='Choose edited table of Level-Up Moves', defaultextension='.csv',filetypes= [('CSV','.csv')])

    #load levelup GARC
    move_edit_data = choose_GARC(move_edit_data, 'Levelup', move_edit_data.game)

    #get data from csv individual binary files
    with open(save_path, 'r', newline = '', encoding='utf-8-sig') as csvfile:
        reader_head = csv.reader(csvfile, dialect='excel', delimiter=',')

        temp_array = list(reader_head)



    #convert levelup move name to all lower case to ease search

    for x in range(len(move_list)):
        move_list[x] = move_list[x].lower()

    #build the new set of binary files

    last_personal = 0
    temp_file = []
    for line_number, line in enumerate(temp_array):
        #no file for header or blank space
        if(line[0] in {'','Personal Index'}):
            pass
        else:
            #if went down, something is very wrong, abort
            if(int(line[0]) < int(last_personal)):
                print('Serious error at line', line_number + 1, 'index numbers out of order, please check the line, you might need to sort the .csv file by index number.')

            #if not-equal, starting next file
            if(line[0] != last_personal):
                #append terminator to previous file
                temp_file.extend([0xFF, 0xFF, 0xFF, 0xFF])
                #append current file to array
                output_array.append(temp_file)
                #clear temp
                temp_file = []
                #update last personal
                last_personal = line[0]

            #get move index
            try:
                temp_index = move_list.index(line[3].lower())
            except Exception as e:
                print('Error at line', line_number + 1, 'Python error:', e)
                try:
                    print('Move entered as', line[3], 'not found. Please check spelling')
                except Exception as e:
                    print('Error 2:', e)
                    print('Unable to access the entered move name, something is wrong.')

            #move index, low byte then high
            temp_file.append(temp_index%0x100)
            temp_file.append(temp_index >> 8)
            #level
            if(int(line[2]) < 0 or int(line[2]) > 100):
                print('Warning, level at line', line_number,'is', line[2],'.\n')
            temp_file.append(int(line[2]))
            #unused
            temp_file.append(0x00)
    #final loop ends without appending last file, handle it now
    temp_file.extend([0xFF, 0xFF, 0xFF, 0xFF])
    output_array.append(temp_file)

    move_edit_data.levelup = output_array
         
   

    save_GARC(move_edit_data, 'levelup')

    return(move_edit_data)


def main():
    move_edit_data = Pokedata()
    action_choice = ''
    
    current_directory = os.getcwd()
    move_list_path = os.path.join(current_directory, 'move_list.csv')

    move_list = []
    pokemon_list = []

    #get generation
    while True:
        temp = input('Enter Generation, (XY, ORAS, SM, USUM)\n').upper()
        if(temp in {'XY', 'ORAS', 'SM', 'USUM'}):
            move_edit_data.game = temp
            break
        else:
            print(temp, 'is not valid\n\n')
        
    pokemon_list_path = os.path.join(current_directory, 'pokemon_list_' + move_edit_data.game + '.csv')

    #load move names
    with open(move_list_path, newline = '', encoding='utf-8-sig') as csvfile:
        reader_head = csv.reader(csvfile, dialect='excel', delimiter=',')
        
        #load csv into an array      
        temp = list(reader_head)

        for line in temp:
            if(line[1] != ''):
                move_list.append(line[1])
            else:
                break
    print('Loaded Move Name List')


    #load pokemon names
    with open(pokemon_list_path, newline = '', encoding='utf-8-sig') as csvfile:
        reader_head = csv.reader(csvfile, dialect='excel', delimiter=',')
        
        #load csv into an array      
        temp = list(reader_head)

        for line in temp:
            if(line[1] != '' or line[0] == '0'):
                pokemon_list.append(line[1])
            else:
                break
    print('Loaded Pokemon Name List')

    while True:

        #choose extract or rebuild
        while True:
            temp = input('Extract or rebuild GARC, or quit? (e/r/q)\n').lower()
            if(temp in {'e', 'r', 'q'}):
                action_choice = temp
                break
            else:
                print(temp, 'is not valid\\nn')

        while action_choice != 'q':
            temp = input('Learnset or TM/HM/Tutor? (L/T)\n').lower()
            if(temp in {'l', 't', 'q'}):
                action_choice = action_choice + temp if temp != 'q' else 'q'
                break
            else:
                print(temp, 'is not valid\\nn')

        match action_choice:
            case 'el':
                export_levelup(move_edit_data, move_list, pokemon_list)
            case 'rl':
                import_levelup(move_edit_data, move_list)
            case 'et':
                export_tmhmtutor(move_edit_data, move_list, pokemon_list)
            case 'rt':
                import_tmhmtutor(move_edit_data, move_list)
            case 'q':
                return


main()