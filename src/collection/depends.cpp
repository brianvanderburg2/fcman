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

#include "depends.h"
#include "package.h"
#include "file.h"
#include "collection.h"


// Constructor
Dependency::Dependency() : m_file(NULL)
{
}

// Construct from XML
Dependency::Dependency(wxXmlNode* node) : m_file(NULL)
{
    m_name = node->GetPropVal(wxT("name"), wxT("untitled"));
    m_minVersion.Set(node->GetPropVal(wxT("minversion"), wxEmptyString));
    m_maxVersion.Set(node->GetPropVal(wxT("maxversion"), wxEmptyString));
}

// Destructor
Dependency::~Dependency()
{
    if(m_file)
        m_file->RemoveDependency(this);
}

// Set the dependency name
void Dependency::SetName(const wxString& name)
{
    if(name != m_name)
    {
        m_name = name;

        if(m_file && m_file->GetCollection())
            m_file->GetCollection()->SetDirty();
    }
}
    
// Set the version information
void Dependency::SetMinVersion(const wxString& version)
{
    if(version != m_minVersion.Get())
    {
        m_minVersion.Set(version);

        if(m_file && m_file->GetCollection())
            m_file->GetCollection()->SetDirty();
    }
}
void Dependency::SetMaxVersion(const wxString& version)
{
    if(version != m_maxVersion.Get())
    {
        m_maxVersion.Set(version);

        if(m_file && m_file->GetCollection())
            m_file->GetCollection()->SetDirty();
    }
}

// Get a display string
wxString Dependency::GetDisplayString() const
{
    wxString result(m_name);
    if(m_minVersion.IsOk())
    {
        result += wxT(" >= ");
        result += m_minVersion.Get();
    }
    if(m_maxVersion.IsOk())
    {
        if(m_minVersion.IsOk())
            result += wxT(",");

        result += wxT(" <= ");
        result += m_maxVersion.Get();
    }

    return result;
}

// Check the package and see if it satifies this dependnecy
bool Dependency::Check(Package* package) const
{
    if(m_name != package->GetName())
        return false;

    const Version& pkgver = package->GetVersionObject();

    if(!pkgver.IsOk())
    {
        if(m_minVersion.IsOk() || m_maxVersion.IsOk())
            return false;
        else
            return true;
    }

    if(m_minVersion.IsOk() && m_minVersion.Compare(pkgver) > 0)
        return false;

    if(m_maxVersion.IsOk() && m_maxVersion.Compare(pkgver) < 0)
        return false;

    return true;
}

// Save
wxXmlNode* Dependency::Save()
{
    wxXmlNode* node = new wxXmlNode(NULL, wxXML_ELEMENT_NODE, wxT("dependency"));
    node->AddProperty(wxT("name"), m_name);
    if(m_minVersion.IsOk())
        node->AddProperty(wxT("minversion"), m_minVersion.Get());
    if(m_maxVersion.IsOk())
        node->AddProperty(wxT("maxversion"), m_maxVersion.Get());

    return node;
}

// Delete the dependency
void Dependency::Delete()
{
    delete this;
}



