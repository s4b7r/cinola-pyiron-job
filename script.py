import pandas as pd
from pathlib import Path
import re
import shutil


import cinola_interface as cin


CINOLA_BASE_PATH = Path(__file__).resolve().parent / 'CINOLA'
CINOLA_EXE = CINOLA_BASE_PATH / 'CINOLA_x64.exe'
RUNSCRIPT = CINOLA_BASE_PATH / 'run-cinola.cmd'
CMD = str(RUNSCRIPT) + ' ' + '"' + str(CINOLA_EXE) + '"'
CINOLA_MM = 'mm.dat'
CINOLA_MM_TEMPLATE = CINOLA_BASE_PATH / CINOLA_MM
CINOLA_CONFIG_FILES = {
                    CINOLA_MM: '',
                    'cinola.aa': 'aniso_axes_string',
                    'cinola.ae': 'aniso_energies_string',
                    'cinola.am': 'aniso_and_moment_assign_string',
                    'cinola.co': 'general_config_string',
                    'cinola.jj': 'jij_assign_string',
                    'cinola.jv': 'jvalues_string',
                    'cinola.mm': 'moments_string',
                    'cinola.nn': 'neighborhoods_string',
                    'cinola.po': 'positions_string'
                    }


def write_input(working_directory, input_dict):
    def write_input_from_files(working_directory, inputfiles_path):
        working_directory = Path(working_directory)
        inputfiles_path = input_dict.get('cinola_inputfiles_path', None)
        if inputfiles_path is not None:
            for filename, _ in CINOLA_CONFIG_FILES.items():
                try:
                    shutil.copy(str((Path(inputfiles_path) / filename).resolve()), str(working_directory / filename))
                except FileNotFoundError:
                    pass

    def write_input_from_dict(working_directory, input_dict):
        structure = input_dict.get('structure')
        Js_K = input_dict.get('Js_K')
        iterations_per_temperature_cinola = input_dict.get('num_iter_per_temp')
        H_value = input_dict.get('H_value')
        T_low = input_dict.get('T_low')
        T_high = input_dict.get('T_high')
        T_step = input_dict.get('T_step')

        neighbor_file = cin.get_neighborhoods_string(structure=structure, Js_K=Js_K)
        Jij_file = cin.get_jvalues_string(Js_K)
        Jij_assign_file = cin.get_jij_assign_string(structure=structure, Js_K=Js_K)
        aniso_axes_file = cin.get_aniso_axes_string(structure)
        aniso_energies_file = cin.get_aniso_energies_string()
        am_assign_file = cin.get_anisotropy_and_moment_assign_string(structure)
        moments_file = cin.get_moments_string(structure)
        position_file = cin.get_positions_string(structure)
        config_file = cin.get_general_config_string(
                                                num_iter_per_temp=iterations_per_temperature_cinola,
                                                H_value=H_value,
                                                T_low=T_low,
                                                T_high=T_high,
                                                T_step=T_step
                                                )

        input_dict['aniso_axes_string'] = aniso_axes_file
        input_dict['aniso_energies_string'] = aniso_energies_file
        input_dict['aniso_and_moment_assign_string'] = am_assign_file
        input_dict['general_config_string'] = config_file
        input_dict['jij_assign_string'] = Jij_assign_file
        input_dict['jvalues_string'] = Jij_file
        input_dict['moments_string'] = moments_file
        input_dict['neighborhoods_string'] = neighbor_file
        input_dict['positions_string'] = position_file
        
        working_directory = Path(working_directory)
        for filename, input_key in CINOLA_CONFIG_FILES.items():
            if input_key != '':
                with open(working_directory / filename, 'w') as file:
                    file.write(input_dict[input_key])

    inputfiles_path = input_dict.get('cinola_inputfiles_path', None)
    if inputfiles_path is not None:
        write_input_from_files(working_directory, inputfiles_path)
    if inputfiles_path is None:
        write_input_from_dict(working_directory, input_dict)
        


def collect_output(working_directory):
    def fix_output_files_csv(paths):
        def fix_acceptance_name_and_unit(paths):
            for path in paths:
                shutil.copy(path, path.parent / f'{path.stem}_Bfixaccaptance')
                with open(path, 'r') as b_file:
                    lines = b_file.readlines()
                with open(path, 'w') as b_file:
                    # pd.read_csv does not like whitespaces in header, if I use it as I do.
                    b_file.write(lines[0].replace('acceptance rate', 'acceptance_rate'))
                    # pd.read_csv also wants the headers to be same size and Cinola does not provide unit for acceptance rate.
                    # Thus, we have to add it here.
                    b_file.write(lines[1].rstrip() + ' 1\n')
                    b_file.writelines(lines[2:])
        
        def combine_name_and_unit(paths):
            for path in paths:
                shutil.copy(path, path.parent / f'{path.stem}_Bcombinenameunit')
                with open(path, 'r') as file:
                    lines = file.readlines()
                names = lines[0].split()
                units = lines[1].split()
                combined = [f'{name}_[{unit}]' for (name, unit) in zip(names, units)]
                combined_line = ' '.join(combined) + '\n'
                with open(path, 'w') as file:
                    file.write(combined_line)
                    file.writelines(lines[2:])

        def add_missing_column_name(paths):
            for path in paths:
                shutil.copy(path, path.parent / f'{path.stem}_Bmissingcol')
                with open(path, 'r') as b_file:
                    lines = b_file.readlines()
                with open(path, 'w') as b_file:
                    b_file.write(lines[0].replace('\t', ' ').replace('  ', ' NO '))
                    b_file.write(lines[1].replace('\t', ' ').replace('  ', ' NO '))
                    b_file.writelines(lines[2:])

        def output_format_cleanup(paths):
            for path in paths:
                shutil.copy(path, path.parent / f'{path.stem}_Boutputformatcleanup')
                with open(path, 'r') as b_file:
                    lines = b_file.readlines()
                with open(path, 'w') as b_file:
                    common_num_fields = 99
                    for lineno, line in enumerate(lines):
                        tokens = line.split()
                        common_num_fields = len(tokens) if len(tokens) < common_num_fields else common_num_fields
                    for line in lines:
                        tokens = line.split()
                        b_file.write(' '.join(tokens[:common_num_fields]) + '\n')

        def proper_name_mag(paths):
            for path in paths:
                shutil.copy(path, path.parent / f'{path.stem}_Bpropernamemag')
                with open(path, 'r') as b_file:
                    lines = b_file.readlines()
                with open(path, 'w') as b_file:
                    b_file.write(lines[0].replace('Mag_[mu_B]', 'MagAvgMag_[mu_B]').replace('Mag_[emu/mol]', 'MagHProjected_[mu_B]'))
                    b_file.writelines(lines[1:])

        output_format_cleanup(paths)
        add_missing_column_name(paths)
        fix_acceptance_name_and_unit(paths)
        combine_name_and_unit(paths)
        # proper_name_mag(paths)

    def get_df_list_for_param(wd, param):
        def get_pathmatchs(wd, param):
            paths_regex = re.compile(f'(.+)_{param}(\\d+\\.\\d+)_run_1_.*\\.txt')
            pathmatchs = []
            for path in wd.glob('*.txt'):
                match = paths_regex.match(str(path.resolve()))
                if not match:
                    continue
                pathmatchs.append({'path': path, 'match': match})
            return pathmatchs

        pathmatchs = get_pathmatchs(wd=wd, param=param)
        fix_output_files_csv([pathmatch['path'] for pathmatch in pathmatchs])

        dfs = []
        for pathmatch in pathmatchs:
            df = pd.read_csv(pathmatch['path'], sep=r'\s+', header=[0])
            dfs.append({f'{param}': pathmatch['match'].group(2), 'df': df})

        return dfs

    def get_b_df_list(wd):
        return get_df_list_for_param(wd=wd, param='B')

    def get_t_df_list(wd):
        return get_df_list_for_param(wd=wd, param='T')

    wd = Path(working_directory)
    return {'B_dfs': get_b_df_list(wd=wd), 'T_dfs': get_t_df_list(wd=wd)}
