request-slice(){
    if [[ $# -lt 2 ]]; then
        echo "Error: insufficient parameters"
        echo "Insert host name and bandwidth"
        return 1
    fi

    if [[ $# -gt 3 ]]; then
        echo "Error: too many parameters"
        echo "Insert host name and bandwidth"
        return 1
    fi

    if [[ $# -eq 2 ]]; then
        if [[ "$1" == "$NAME" ]]; then
            echo "Error: you cannot create a slice with yourself"
            return 1
        fi
        curl http://controller:8080/slice/$NAME/$1 --json '{"bandwidth": '"$2"'}';
        echo;
    fi

    if [[ $# -eq 3 ]]; then
        if [[ "$1" == "$2" ]]; then
            echo "Error: you cannot create a slice with yourself"
            return 1
        fi
        curl http://controller:8080/slice/$1/$2 --json '{"bandwidth": '"$3"'}';
        echo;
    fi
}


delete-slice(){
    if [[ $# -eq 0 ]]; then
        curl http://controller:8080/slice/$NAME -X DELETE;
    fi
    
    if [[ $# -eq 1 ]]; then
        if [[ "$1" == "$NAME" ]]; then
            echo "Error: host name is equal to your current host name, pleas insert a different host name"
            return 1
        fi
        curl http://controller:8080/slice/$NAME/$1 -X DELETE;
        echo;
    fi

    if [[ $# -eq 2 ]]; then
        curl http://controller:8080/slice/$1/$2 -X DELETE;
        echo;
    fi

    if [[ $# -gt 2 ]]; then
        echo "Error: too many parameters"
        return 1
    fi
}

slice-info(){
    if [[ $# -lt 1 ]]; then
        echo "Error: insufficient parameters"
        echo "2 parameters needed"
        echo "Please insert 2 host names"
        return 1
    fi

    if [[ $# -gt 2 ]]; then
        echo "Error: too many parameters"
        echo "Insert 2 host names"
        return 1
    fi

    if [[ $# -eq 1 ]]; then
        curl http://controller:8080/slice/$NAME/$1 -X GET;
        echo;
    fi

    if [[ $# -eq 2  ]]; then
        curl http://controller:8080/slice/$1/$2 -X GET;
        echo;
    fi
}

update-slice(){
    if [[ $# -lt 2 ]]; then
        echo "Error: insufficient parameters"
        echo "Please inert a host name and a bandwidth"
        return 1
    fi
    if [[ $# -gt 3 ]]; then
        echo "Error: too many parameters"
        echo "Please insert a host name and a bandwidth"
        return 1
    fi
    if [[ $# -eq 2 ]]; then
        curl http://controller:8080/slice/$NAME/$1 --json '{"bandwidth": '"$2"'}' -X PUT;
        echo;
    fi
    if [[ $# -eq 3 ]]; then
        curl http://controller:8080/slice/$1/$2 --json '{"bandwidth": '"$3"'}' -X PUT;
        echo;
    fi
}
