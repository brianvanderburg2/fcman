// This file is part of File Collection Manager
// Copyright (C) 2009 Brian Allen Vanderburg II
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.


// Requirements
#include <wx/defs.h>
#include <wx/string.h>
#include <wx/xml/xml.h>

#include "package.h"
#include "file.h"
#include "collection.h"


// Constructor
Package::Package() : m_file(NULL)
{
}

// Construct from XML
Package::Package(wxXmlNode* node) : m_file(NULL)
{
    m_name = node->GetPropVal(wxT("name"), wxT("untitled"));
    m_version.Set(node->GetPropVal(wxT("version"), wxEmptyString));
}

// Destructor
Package::~Package()
{
    if(m_file)
        m_file->RemovePackage(this);
}

// Set the package name
void Package::SetName(const wxString& name)
{
    if(name != m_name)
    {
        m_name = name;

        if(m_file && m_file->GetCollection())
            m_file->GetCollection()->SetDirty();
    }
}
    
// Set the version information
void Package::SetVersion(const wxString& version)
{
    if(version != m_version.Get())
    {
        m_version.Set(version);

        if(m_file && m_file->GetCollection())
            m_file->GetCollection()->SetDirty();
    }
}

// Get a display string
wxString Package::GetDisplayString() const
{
    wxString result(m_name);
    if(m_version.IsOk())
    {
        result += wxT(" ");
        result += m_version.Get();
    }

    return result;
}

// Save
wxXmlNode* Package::Save()
{
    wxXmlNode* node = new wxXmlNode(NULL, wxXML_ELEMENT_NODE, wxT("package"));
    node->AddProperty(wxT("name"), m_name);
    if(m_version.IsOk())
        node->AddProperty(wxT("version"), m_version.Get());

    return node;
}

// Delete the package
void Package::Delete()
{
    delete this;
}



