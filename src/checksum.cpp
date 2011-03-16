// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/arrstr.h>
#include <wx/buffer.h>
#include <wx/strconv.h>
#include <wx/string.h>

#include <mhash.h>

#include "checksum.h"


// Implementation detials
struct ChecksumCalculator::Impl
{
    MHASH hash;
};

// Available types
static const struct
{
    const wxChar* name;
    hashid id;
} gs_types[] =
{
    { wxT("MD5"), MHASH_MD5 },
    { wxT("SHA1"), MHASH_SHA1 },
    { wxT("SHA224"), MHASH_SHA224 },
    { wxT("SHA256"), MHASH_SHA256 },
    { wxT("SHA384"), MHASH_SHA384 },
    { wxT("SHA512"), MHASH_SHA512 },
    { NULL, static_cast<hashid>(0) }
};

// Does a certain type exist
bool ChecksumCalculator::Exists(const wxString& type)
{
    for(size_t pos = 0; gs_types[pos].name; pos++)
    {
        wxString name(gs_types[pos].name);
        if(name.Upper() == type.Upper())
            return true;
    }

    return false;
}

// Enumerate available types
wxArrayString ChecksumCalculator::GetTypes()
{
    wxArrayString results;

    for(size_t pos = 0; gs_types[pos].name; pos++)
    {
        wxString name(gs_types[pos].name);
        results.Add(name.Upper());
    }

    return results;
}

// Constructor
ChecksumCalculator::ChecksumCalculator(const wxString& type) :
    m_impl(NULL)
{
    // Find checksum type if entire checksum is passed in
    wxString _type;

    int index = type.Find(wxT(':'));
    if(index)
    {
        _type = type.Mid(0, index);
    }
    else
    {
        _type = type;
    }

    // Determine the hash id
    hashid id;
    size_t pos;
    for(pos = 0; gs_types[pos].name; pos++)
    {
        wxString name(gs_types[pos].name);
        if(name.Upper() == _type.Upper())
        {
            id = gs_types[pos].id;
            break;
        }
    }

    if(gs_types[pos].name == NULL)
        return;

    // Found the hash type
    m_impl = new ChecksumCalculator::Impl;
    m_impl->hash = mhash_init(id);
    if(m_impl->hash == MHASH_FAILED)
    {
        delete m_impl;
        m_impl = NULL;
        return;
    }
}

// Destructor
ChecksumCalculator::~ChecksumCalculator()
{
    if(m_impl)
        delete m_impl;
}

// Update the checksum
void ChecksumCalculator::Update(void* data, size_t len)
{
    mhash(m_impl->hash, data, len);
}

// Get the checksum string in the form type:value
wxString ChecksumCalculator::Finish()
{
    // Allocate hash buffer
    hashid id = mhash_get_mhash_algo(m_impl->hash);
    size_t size = mhash_get_block_size(id);

    wxMemoryBuffer buffer(size);
    unsigned char* cbuf = static_cast<unsigned char*>(buffer.GetData());

    // Finalize hashing algorithm and get result
    mhash_deinit(m_impl->hash, cbuf);
    delete m_impl;
    m_impl = NULL;

    // Prepare the result string
    const wxChar *hex = wxT("0123456789ABCDEF");
    wxString result;
    size_t pos;

    for(pos = 0; gs_types[pos].name; pos++)
    {
        if(gs_types[pos].id == id)
        {
            result = gs_types[pos].name;
        }  
    }

    result += wxT(":");

    for(pos = 0; pos < size; pos++)
    {
        result += hex[(cbuf[pos] & 0xF0) >> 4];
        result += hex[cbuf[pos] & 0x0F];
    }

    return result;
}



