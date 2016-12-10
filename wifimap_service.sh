#! /bin/bash

### BEGIN INIT INFO
# Provides:          wifimap.sh
# Required-Start:    gpsd
# Should-Start:      
# Required-Stop:     
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# X-Start-Before:    
# Short-Description: wifimap daemon 
# Description:       wifimap description
### END INIT INFO

. /lib/init/vars.sh
. /lib/lsb/init-functions


PIDFILE=/var/lock/wifimap.pid

# Carry out specific functions when asked to by the system
case "$1" in
  start)
    echo 'Starting script wifimap'
	start-stop-daemon -b --start --exec  path/to/service.sh
    ;;
  stop)
    echo 'Stopping script blah'
    echo 'Could do more here'
    ;;
  *)
    echo 'Usage: /etc/init.d/blah {start|stop}'
    exit 1
    ;;
esac

exit 0

