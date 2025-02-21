from ydata_profiling import ProfileReport
from app import df 

profile = ProfileReport(df, title="Pandas Profiling Report")
profile.to_widgets()

#issue pertaining to the ydata_profiling library not being able to be imported
#I tried to install the library but it did not work