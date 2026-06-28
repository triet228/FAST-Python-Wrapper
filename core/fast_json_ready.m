function value = fast_json_ready(value)

if isa(value, 'function_handle')
    value = func2str(value);
    return
end

if isstruct(value)
    fields = fieldnames(value);

    for ii = 1:numel(value)
        for jj = 1:numel(fields)
            value(ii).(fields{jj}) = fast_json_ready(value(ii).(fields{jj}));
        end
    end

    return
end

if iscell(value)
    for ii = 1:numel(value)
        value{ii} = fast_json_ready(value{ii});
    end
end

end
