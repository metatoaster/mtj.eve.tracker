def format_timedelta(delta_t):
    hours = delta_t.seconds / 3600
    days = delta_t.days
    seconds = delta_t.seconds

    # Don't ask.  Read the test; be happy you don't have to write this.
    # (WTB something simple like str(delta_t) with more control.)
    # (Maybe I should just do this in javascript?)
    return '%(day)s%(hour)s' % {
        'day': days and '%(days)d day%(dayp)s%(comma)s' % {
                'days': days,
                'dayp': days != 1 and 's' or '',
                'comma': seconds > 3599 and ', ' or '',
            } or '',
        'hour': (hours > 0 or days == 0 and hours == 0)
            and '%(hours)d hour%(hourp)s' % {
                'hours': hours,
                'hourp': hours != 1 and 's' or '',
            } or '',
    }
