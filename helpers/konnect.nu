export def kdevices [] {
  ^docker ps -f "name=^kathara\\_.+$" --format json | lines | each { from json }
  | select ID Command Image Names State
  | insert device { |row|
   $row.Names | parse -r "^kathara_.*_(?<device>\\w+)_.+$" | get device.0
  }
}

def "nu-complete kathara-devices" [] {
  kdevices
    | each {|row| { value: $row.device, description: $"($row.Command) in ($row.Image)" } }
}

# Connects to a specific device's Docker container.
#
# This command searches for a running Docker container whose name 
# matches the pattern `_<device>_` and drops you into an interactive 
# bash session inside that container.
@example "Connect to host3" {konnect host3} --result "root@host3:/#"
export def konnect [
    device: string@"nu-complete kathara-devices" # The name of the device to connect to
] {
  let container = (^docker ps -qf $"name=^kathara\\_.+\\_($device)\\_.+$" | str trim)
  
  if ($container | is-empty) {
    print $"Error: Device '($device)' not found or container is not running."
  } else {
    ^docker exec -ti $container /bin/bash
  }
}
