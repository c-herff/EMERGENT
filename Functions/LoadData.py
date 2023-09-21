import pandas as pd
import numpy as np

def get_patient_phase_main(df_main_patient_phases, patient, dates):
    """
    Get the main phase of the patient on a certain date.
    @param df_main_patient_phases: a data frame with the dates of the different main phases of the patients
    @param patient: patient name/synonym.
    @param dates: a series of dates
    @return: a series of main phases
    """

    preop_start = df_main_patient_phases.loc[patient, 'preop'].date()
    lesion_start = df_main_patient_phases.loc[patient, 'lesion'].date()
    finetune_start = df_main_patient_phases.loc[patient, 'finetune'].date()

    df_phases = pd.DataFrame(columns=['date','phase'])
    df_phases['date'] = dates
    
    # set phase to none where date is before preop_start
    df_phases.loc[pd.to_datetime(df_phases['date']).dt.date < preop_start, 'phase'] = 'none'

    # set phase to preop where date is between preop_start and lesion_start
    df_phases.loc[(pd.to_datetime(df_phases['date']).dt.date >= preop_start) & (pd.to_datetime(df_phases['date']).dt.date < lesion_start), 'phase'] = 'preop'

    # set phase to lesion where date is between lesion_start and finetune_start
    df_phases.loc[(pd.to_datetime(df_phases['date']).dt.date >= lesion_start) & (pd.to_datetime(df_phases['date']).dt.date < finetune_start), 'phase'] = 'lesion'

    # set phase to finetune where date is after finetune_start
    df_phases.loc[pd.to_datetime(df_phases['date']).dt.date >= finetune_start, 'phase'] = 'finetune'

    return df_phases['phase']

def get_patient_phase_fine(df_fine_patient_phases, dates):
    """
    Get the fine phase of the patient on a certain date.
    @param df_fine_patient_phases: a data frame with the dates of the different fine phases of the patients
    @param dates: a series of dates
    @return: a series of fine phases
    """

    phases = df_fine_patient_phases['phase'].unique()
    df_phases = pd.DataFrame(columns=['date','phase'])
    df_phases['date'] = dates
    df_phases.loc[:,'phase'] = 'none'

    for i in range(1, len(phases)):
        phase_start = df_fine_patient_phases['date'][df_fine_patient_phases['phase'] == phases[i-1]].iloc[0].date()
        phase_end = df_fine_patient_phases['date'][df_fine_patient_phases['phase'] == phases[i]].iloc[0].date()
        df_phases.loc[(pd.to_datetime(df_phases['date']).dt.date >= phase_start) & (pd.to_datetime(df_phases['date']).dt.date < phase_end), 'phase'] = phases[i-1]

    df_phases.loc[pd.to_datetime(df_phases['date']).dt.date >= phase_end, 'phase'] = phases[-1]

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
        df_med = pd.read_csv('{}/{}/{}_med_{}.csv'.format(path,patient, patient, phase), sep=';')
        df_med['time'] = pd.to_datetime(df_med['time'],format= '%H:%M' ).dt.time
        medication_settings[phase] = df_med

    # Load DBS settings
    dbs_settings = {}
    for phase in df_fine_patient_phases['phase'].unique():
        df_dbs = pd.read_csv('{}/{}/{}_DBS_{}.csv'.format(path,patient, patient, phase), sep=';')
        dbs_settings[phase] = df_dbs
    # Create DataFrame
    s=None
    for key in dbs_settings.keys():
        a = dbs_settings[key]
        a['phase']=key
        if type(s)==pd.core.frame.DataFrame:
            s = pd.concat([s,pd.DataFrame(a)])
        else:
            s = pd.DataFrame(a)
    dbs_settings=s

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
    df_combined['phase_fine'] = get_patient_phase_fine(df_fine_patient_phases, df_combined['time'])

    df_fine_patient_phases = pd.merge(df_fine_patient_phases,dbs_settings,on='phase')

    # Return the combined data frame
    return df_combined, df_fine_patient_phases, medication_settings