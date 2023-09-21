import pandas as pd
import numpy as np

def get_patient_phase_main(df_main_patient_phases, patient, dates):
    """
    Get the main phase of the patient on a certain date.
    @param df_main_patient_phases: a data frame with the dates of the different main phases of the patients
    @param patient: patient name/synonym.
    @param dates: a series of dates
    @return: a series of phases
    """

    df_phases = pd.DataFrame(columns=['date','phase'])
    df_phases['date'] = dates
    df_phases['phase'][pd.to_datetime(df_phases['date']).dt.date < df_main_patient_phases.loc[patient, 'preop'].date()] = 'none'
    df_phases['phase'][(pd.to_datetime(df_phases['date']).dt.date >= df_main_patient_phases.loc[patient, 'preop'].date()) & (pd.to_datetime(df_phases['date']).dt.date < df_main_patient_phases.loc[patient, 'lesion'].date())] = 'preop'
    df_phases['phase'][(pd.to_datetime(df_phases['date']).dt.date >= df_main_patient_phases.loc[patient, 'lesion'].date()) & (pd.to_datetime(df_phases['date']).dt.date < df_main_patient_phases.loc[patient, 'finetune'].date())] = 'lesion'
    df_phases['phase'][pd.to_datetime(df_phases['date']).dt.date >= df_main_patient_phases.loc[patient, 'finetune'].date()] = 'finetune'

    return df_phases['phase']

def get_data(patient,path='./data/'):
    """
    Load the CSV files of the patient and return a data frame with all the data.
    @param patient: patient name/synonym.
    """

    # Load the CSV files
    df_dyskinesia = pd.read_csv('{}/{}/{}_dyskinesia.csv'.format(path,patient, patient))
    df_tremor = pd.read_csv('{}/{}/{}_tremor.csv'.format(path,patient, patient))
    df_tremor_severity = pd.read_csv('{}/{}/{}_tremor_severity.csv'.format(path,patient, patient))
    df_fine_patient_phases = pd.read_csv('{}/{}/{}_phases.csv'.format(path,patient, patient), sep=';', parse_dates=['date'], dayfirst=True)

    # Load medication settings
    medication_settings = {}
    for phase in df_fine_patient_phases['phase'].unique():
        df_med = pd.read_csv('{}/{}/{}_med_{}.csv'.format(path,patient, patient, phase), sep=';', parse_dates=['time'], dayfirst=True)
        medication_settings[phase] = df_med

    # Load DBS settings
    dbs_settings = {}
    for phase in df_fine_patient_phases['phase'].unique():
        df_dbs = pd.read_csv('{}/{}/{}_DBS_{}.csv'.format(path,patient, patient, phase), sep=';')
        dbs_settings[phase] = df_dbs

    # Load the different patient phases
    df_main_patient_phases = pd.read_csv('{}/dates.csv'.format(path), index_col=0, sep=';', parse_dates=['preop', 'lesion', 'finetune'], dayfirst=True)

    # Convert the time column to DateTime
    df_dyskinesia['time'] = pd.to_datetime(df_dyskinesia['time'], unit='s')
    df_tremor['time'] = pd.to_datetime(df_tremor['time'], unit='s')
    df_tremor_severity['time'] = pd.to_datetime(df_tremor_severity['time'], unit='s')

    # Remove all rows with all NaN values in all columns except time
    df_dyskinesia = df_dyskinesia.dropna(how='all', subset=df_dyskinesia.columns[1:])
    df_tremor = df_tremor.dropna(how='all', subset=df_tremor.columns[1:])
    df_tremor_severity = df_tremor_severity.dropna(how='all', subset=df_tremor_severity.columns[1:])

    # Find the start and end date of the data 
    # (assuming the data is sorted and all three data frames have the same length)
    start_date = df_dyskinesia.iloc[0]['time'].date()
    end_date = df_dyskinesia.iloc[len(df_dyskinesia)-1]['time'].date()

    # Check if start and end date are the same for all three data frames
    if not(start_date == df_tremor.iloc[0]['time'].date() and end_date == df_tremor.iloc[len(df_tremor)-1]['time'].date()):
        raise Exception("Start or end date of tremor data frame is different from dyskinesia data frame")
    if not(start_date == df_tremor_severity.iloc[0]['time'].date() and end_date == df_tremor_severity.iloc[len(df_tremor_severity)-1]['time'].date()):
        raise Exception("Start or end date of tremor_severity dataframe is different from dyskinesia dataframe")

    # Create a continuous data frame combining all three data frames
    df_combined = pd.DataFrame({'time': pd.date_range(start=start_date, end=end_date+pd.Timedelta(days=1), freq='1min')})
    
    # Add all columns (except time) to the combined data frame:
    for col in df_dyskinesia.columns[1:]:
        df_combined[col + "_dyskinesia"] = np.nan
        df_combined.loc[df_combined['time'].isin(df_dyskinesia['time']), col + "_dyskinesia"] = df_dyskinesia.loc[df_dyskinesia['time'].isin(df_combined['time']), col].values

    for col in df_tremor.columns[1:]:
        df_combined[col + "_tremor"] = np.nan
        df_combined.loc[df_combined['time'].isin(df_tremor['time']), col + "_tremor"] = df_tremor.loc[df_tremor['time'].isin(df_combined['time']), col].values

    for col in df_tremor_severity.columns[1:]:
        df_combined[col + "_tremor_severity"] = np.nan
        df_combined.loc[df_combined['time'].isin(df_tremor_severity['time']), col + "_tremor_severity"] = df_tremor_severity.loc[df_tremor_severity['time'].isin(df_combined['time']), col].values
    
    # Remove the last row (this one contains always the end_date plus one day at 00:00:00)
    df_combined = df_combined.iloc[:-1]

    # Add patient phase
    df_combined['phase_main'] = get_patient_phase_main(df_main_patient_phases, patient, df_combined['time'])

    # Return the combined data frame
    return df_combined, df_fine_patient_phases, medication_settings, dbs_settings